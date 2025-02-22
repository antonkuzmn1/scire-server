import json

import httpx
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect

from app.dependencies.services import get_ticket_service, get_message_service
from app.logger import logger
from app.models import Ticket
from app.schemas.message import MessageCreate, MessageFileCreate
from app.schemas.ticket import TicketCreate, TicketFileCreate, TicketUpdate
from app.services.message_service import MessageService
from app.services.ticket_service import TicketService
from app.settings import settings

router = APIRouter(tags=["WebSocket"])

users_connections = {}
admins_connections = {}


@router.websocket("/")
async def websocket_endpoint(
        websocket: WebSocket,
        ticket_service: TicketService = Depends(get_ticket_service),
        message_service: MessageService = Depends(get_message_service),
):
    protocols = websocket.headers.get("sec-websocket-protocol")
    if not protocols:
        await websocket.close(code=1008, reason="No token")
        return
    token = protocols.split(",")[-1].strip()
    if not token:
        await websocket.close(code=1008, reason="No token")
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OAUTH_CHECK_URL}/check",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            account_data = response.json()
    except httpx.HTTPStatusError as e:
        await websocket.close(code=1008, reason=f"Auth service error: {e.response.text}")
        return
    except httpx.RequestError as e:
        await websocket.close(code=1008, reason=f"Auth service unavailable: {str(e)}")
        return
    except Exception as e:
        await websocket.close(code=1008, reason=f"Unexpected error: {str(e)}")
        return

    role = account_data["role"]
    account_id = account_data["id"]

    await websocket.accept(headers=[(b"Sec-WebSocket-Protocol", token.encode("utf-8"))])

    match role:
        case "user":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.OAUTH_CHECK_URL}/users/profile",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=3.0
                    )
                    response.raise_for_status()
                    profile = response.json()
            except httpx.HTTPStatusError as e:
                await websocket.close(code=1008, reason=f"Auth service error: {e.response.text}")
                return
            except httpx.RequestError as e:
                await websocket.close(code=1008, reason=f"Auth service unavailable: {str(e)}")
                return
            except Exception as e:
                await websocket.close(code=1008, reason=f"Unexpected error: {str(e)}")
                return
            users_connections[account_id] = (websocket, profile)
        case "admin":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.OAUTH_CHECK_URL}/admins/profile",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=3.0
                    )
                    response.raise_for_status()
                    profile = response.json()
            except httpx.HTTPStatusError as e:
                await websocket.close(code=1008, reason=f"Auth service error: {e.response.text}")
                return
            except httpx.RequestError as e:
                await websocket.close(code=1008, reason=f"Auth service unavailable: {str(e)}")
                return
            except Exception as e:
                await websocket.close(code=1008, reason=f"Unexpected error: {str(e)}")
                return
            admins_connections[account_id] = (websocket, profile)
        case _:
            await websocket.close(code=1008, reason=f"Incorrect role: {role}")
            return

    logger.info(f"Client connected: {websocket.client}")

    try:
        while True:
            payloadString = await websocket.receive_text()
            payload = json.loads(payloadString)
            action = payload["action"]
            data = payload["data"]
            logger.info(f"Received message: {payload}")

            match role:
                case "user":
                    match action:
                        case "create_ticket":
                            user_id = account_id
                            user = users_connections[user_id][1]
                            user_ws = users_connections[user_id][0]
                            company_id = user["company_id"]
                            title = data["title"]
                            description = data["description"]
                            ticket = TicketCreate(
                                title=title,
                                description=description,
                                user_id=user_id,
                            )
                            record = await ticket_service.create(ticket)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": action, "data": record}))
                            user_ws.send(json.dumps({"action": action, "data": record}))
                            return
                        case "add_file_to_ticket":
                            user_id = account_id
                            user = users_connections[user_id][1]
                            user_ws = users_connections[user_id][0]
                            company_id = user["company_id"]
                            item_id = data["item_id"]
                            ticket = await ticket_service.get_by_id(item_id)
                            if not ticket:
                                user_ws.send(json.dumps({"action": action, "error": "Ticket not found"}))
                                return
                            if ticket.user_id != user_id:
                                user_ws.send(json.dumps({"action": action, "error": "Access denied"}))
                            file_uuid = data["file_uuid"]
                            file_name = data["file_name"]
                            file_size = data["file_size"]
                            ticket_file = TicketFileCreate(
                                item_id=item_id,
                                file_uuid=file_uuid,
                                file_name=file_name,
                                file_size=file_size,
                            )
                            record = await ticket_service.add_file(ticket_file)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": action, "data": record}))
                            user_ws.send(json.dumps({"action": action, "data": record}))
                            return
                        case "close_ticket":
                            user_id = account_id
                            user = users_connections[user_id][1]
                            user_ws = users_connections[user_id][0]
                            company_id = user["company_id"]
                            item_id = data["item_id"]
                            ticket_old = await ticket_service.get_by_id(item_id)
                            if not ticket_old:
                                user_ws.send(json.dumps({"action": action, "error": "Ticket not found"}))
                                return
                            if ticket_old.user_id != user_id:
                                user_ws.send(json.dumps({"action": action, "error": "Access denied"}))
                            ticket = TicketUpdate(
                                title=ticket_old.title,
                                description=ticket_old.description,
                                status=2,
                                user_id=ticket_old.user_id,
                                admin_id=ticket_old.admin_id
                            )
                            record = await ticket_service.update(item_id, ticket)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": action, "data": record}))
                            user_ws.send(json.dumps({"action": action, "data": record}))
                            message = MessageCreate(
                                text='',
                                user_id=user_id,
                                ticket_id=record.id,
                                solved=True,
                            )
                            message_record = await message_service.create(message)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": "send_message", "data": message_record}))
                            user_ws.send(json.dumps({"action": "send_message", "data": message_record}))
                            return
                        case "send_message":
                            user_id = account_id
                            user = users_connections[user_id][1]
                            user_ws = users_connections[user_id][0]
                            company_id = user["company_id"]
                            text = data["text"]
                            ticket_id = data["ticket_id"]
                            ticket_old = await ticket_service.get_by_id(ticket_id)
                            if not ticket_old:
                                user_ws.send(json.dumps({"action": action, "error": "Ticket not found"}))
                                return
                            if ticket_old.user_id != user_id:
                                user_ws.send(json.dumps({"action": action, "error": "Access denied"}))
                            message = MessageCreate(
                                text=text,
                                user_id=user_id,
                                ticket_id=ticket_id,
                            )
                            record = await message_service.create(message)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": action, "data": record}))
                            user_ws.send(json.dumps({"action": action, "data": record}))
                            return
                        case "add_file_to_message":
                            user_id = account_id
                            user = users_connections[user_id][1]
                            user_ws = users_connections[user_id][0]
                            company_id = user["company_id"]
                            item_id = data["item_id"]
                            message = await message_service.get_by_id(item_id)
                            if not message:
                                user_ws.send(json.dumps({"action": action, "error": "Message not found"}))
                                return
                            if message.user_id != user_id:
                                user_ws.send(json.dumps({"action": action, "error": "Access denied"}))
                            file_uuid = data["file_uuid"]
                            file_name = data["file_name"]
                            file_size = data["file_size"]
                            message_file = MessageFileCreate(
                                item_id=item_id,
                                file_uuid=file_uuid,
                                file_name=file_name,
                                file_size=file_size,
                            )
                            record = await message_service.add_file(message_file)
                            for i in admins_connections:
                                admin_ws = users_connections[i][0]
                                admin = users_connections[i][1]
                                admin_companies = admin["companies"]
                                admin_companies_ids = [company['id'] for company in admin_companies]
                                if company_id in admin_companies_ids:
                                    admin_ws.send(json.dumps({"action": action, "data": record}))
                            user_ws.send(json.dumps({"action": action, "data": record}))
                            return
                        case _:
                            await websocket.close(code=1008, reason=f"Unexpected message: {payload}")
                case "admin":
                    match action:
                        case "assign_ticket":
                            print(payload)
                        case "set_ticket_status_pending":
                            print(payload)
                        case "set_ticket_status_in_progress":
                            print(payload)
                        case "set_ticket_status_closed":
                            print(payload)
                        case "send_message":
                            print(payload)
                        case "add_file_to_message":
                            print(payload)
                        case _:
                            await websocket.close(code=1008, reason=f"Unexpected message: {payload}")
                case _:
                    await websocket.close(code=1008, reason=f"Incorrect role: {role}")
                    return

            for account_id in users_connections:
                websocket, profile = users_connections[account_id]
                await websocket.send_text(f"Echo: {payload}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {websocket.client}")
        del users_connections[account_id]

    except Exception as e:
        logger.warning(f"Error WebSocket: {e}")
        del users_connections[account_id]
        await websocket.close()
