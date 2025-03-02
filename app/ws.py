import json

import httpx
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect

from app.dependencies.services import get_ticket_service, get_message_service
from app.logger import logger
from app.schemas.message import MessageCreate, MessageFileCreate
from app.schemas.ticket import TicketCreate, TicketFileCreate, TicketUpdate
from app.services.message_service import MessageService
from app.services.ticket_service import TicketService
from app.settings import settings

router = APIRouter(tags=["WebSocket"])

users_connections = []
admins_connections = []


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
            users_connections.append((websocket, profile))
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
            admins_connections.append((websocket, profile))
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
                            await user_create_ticket(
                                account_id,
                                ticket_service,
                                data['title'],
                                data['description'],
                            )
                        case "add_file_to_ticket":
                            await user_add_file_to_ticket(
                                account_id,
                                ticket_service,
                                data['item_id'],
                                data['file_uuid'],
                                data['file_name'],
                                data['file_size'],
                            )
                        case "close_ticket":
                            await user_close_ticket(
                                account_id,
                                ticket_service,
                                message_service,
                                data['item_id'],
                            )
                        case "reopen_ticket":
                            await user_reopen_ticket(
                                account_id,
                                ticket_service,
                                message_service,
                                data['item_id'],
                            )
                        case "send_message":
                            await user_send_message(
                                account_id,
                                ticket_service,
                                message_service,
                                data['text'],
                                data['ticket_id'],
                            )
                        case "add_file_to_message":
                            await user_add_file_to_message(
                                account_id,
                                message_service,
                                data['item_id'],
                                data['file_uuid'],
                                data['file_name'],
                                data['file_size'],
                            )
                        case _:
                            await websocket.close(code=1008, reason=f"Unexpected message: {payload}")
                case "admin":
                    match action:
                        case "connect_ticket":
                            await admin_connect_ticket(
                                account_id,
                                ticket_service,
                                message_service,
                                token,
                                data['item_id'],
                            )
                        case "disconnect_ticket":
                            await admin_disconnect_ticket(
                                account_id,
                                ticket_service,
                                message_service,
                                token,
                                data['item_id'],
                            )
                        case "set_ticket_status":
                            await admin_set_ticket_status(
                                account_id,
                                ticket_service,
                                message_service,
                                token,
                                data['item_id'],
                                data['status'],
                            )
                        case "send_message":
                            await admin_send_message(
                                account_id,
                                ticket_service,
                                message_service,
                                token,
                                data['text'],
                                data['user_id'],
                                data['ticket_id'],
                            )
                        case "add_file_to_message":
                            pass
                        case _:
                            await websocket.close(code=1008, reason=f"Unexpected message: {payload}")
                            users_connections[:] = [conn for conn in users_connections if conn[0] != websocket]
                            admins_connections[:] = [conn for conn in admins_connections if conn[0] != websocket]
                case _:
                    await websocket.close(code=1008, reason=f"Incorrect role: {role}")
                    users_connections[:] = [conn for conn in users_connections if conn[0] != websocket]
                    admins_connections[:] = [conn for conn in admins_connections if conn[0] != websocket]

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {websocket.client}")
        users_connections[:] = [conn for conn in users_connections if conn[0] != websocket]
        admins_connections[:] = [conn for conn in admins_connections if conn[0] != websocket]

    except Exception as e:
        logger.warning(f"Error WebSocket: {e}")
        users_connections[:] = [conn for conn in users_connections if conn[0] != websocket]
        admins_connections[:] = [conn for conn in admins_connections if conn[0] != websocket]
        await websocket.close()


async def user_create_ticket(
        account_id: int,
        ticket_service: TicketService,
        title: str,
        description: str
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    ticket = TicketCreate(
        title=title,
        description=description,
        user_id=account_id,
    )

    record = await ticket_service.create(ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "create_ticket", "data": record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "create_ticket", "data": record_dict})


async def user_add_file_to_ticket(
        account_id: int,
        ticket_service: TicketService,
        item_id: int,
        file_uuid: str,
        file_name: str,
        file_size: int
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    ticket = await ticket_service.get_by_id(item_id)
    if not ticket:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "add_file_to_ticket", "error": "Ticket not found"})
        return
    if ticket.user_id != account_id:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "add_file_to_ticket", "error": "Access denied"})
        return

    ticket_file = TicketFileCreate(
        item_id=item_id,
        file_uuid=file_uuid,
        file_name=file_name,
        file_size=file_size,
    )

    record = await ticket_service.add_file(ticket_file)

    # noinspection PyUnresolvedReferences
    record_dict = {
        "item_id": record.item_id,
        "file_uuid": record.file_uuid,
        "file_name": record.file_name,
        "file_size": record.file_size,
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "add_file_to_ticket", "data": record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "add_file_to_ticket", "data": record_dict})


async def user_close_ticket(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        item_id: int,
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    ticket_old = await ticket_service.get_by_id(item_id)
    if not ticket_old:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "close_ticket", "error": "Ticket not found"})
        return
    if ticket_old.user_id != account_id:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "close_ticket", "error": "Access denied"})
        return

    ticket = TicketUpdate(
        title=ticket_old.title,
        description=ticket_old.description,
        status=2,
        user_id=ticket_old.user_id,
        admin_id=ticket_old.admin_id
    )

    record = await ticket_service.update(item_id, ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "close_ticket", "data": record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "close_ticket", "data": record_dict})

    message = MessageCreate(
        text='',
        user_id=account_id,
        ticket_id=record.id,
        solved=True,
    )

    message_record = await message_service.create(message)

    message_record_dict = {
        "id": message_record.id,
        "text": message_record.text,
        "user_id": message_record.user_id,
        "admin_id": message_record.admin_id,
        "ticket_id": message_record.ticket_id,
        "admin_connected": message_record.admin_connected,
        "admin_disconnected": message_record.admin_disconnected,
        "in_progress": message_record.in_progress,
        "solved": message_record.solved,
        "created_at": message_record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": message_record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "send_message", "data": message_record_dict})


async def user_reopen_ticket(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        item_id: int,
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    ticket_old = await ticket_service.get_by_id(item_id)
    if not ticket_old:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "reopen_ticket", "error": "Ticket not found"})
        return
    if ticket_old.user_id != account_id:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "reopen_ticket", "error": "Access denied"})
        return

    ticket = TicketUpdate(
        title=ticket_old.title,
        description=ticket_old.description,
        status=0,
        user_id=ticket_old.user_id,
        admin_id=ticket_old.admin_id
    )

    record = await ticket_service.update(item_id, ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "reopen_ticket", "data": record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "reopen_ticket", "data": record_dict})

    message = MessageCreate(
        text='',
        user_id=account_id,
        ticket_id=record.id,
    )

    message_record = await message_service.create(message)

    message_record_dict = {
        "id": message_record.id,
        "text": message_record.text,
        "user_id": message_record.user_id,
        "admin_id": message_record.admin_id,
        "ticket_id": message_record.ticket_id,
        "admin_connected": message_record.admin_connected,
        "admin_disconnected": message_record.admin_disconnected,
        "in_progress": message_record.in_progress,
        "solved": message_record.solved,
        "created_at": message_record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": message_record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "send_message", "data": message_record_dict})


async def user_send_message(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        text: str,
        ticket_id: int,
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    ticket_old = await ticket_service.get_by_id(ticket_id)
    if not ticket_old:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "send_message", "error": "Ticket not found"})
        return
    if ticket_old.user_id != account_id:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "send_message", "error": "Access denied"})
        return

    message = MessageCreate(
        text=text,
        user_id=account_id,
        ticket_id=ticket_id,
    )

    record = await message_service.create(message)

    record_dict = {
        "id": record.id,
        "text": record.text,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "ticket_id": record.ticket_id,
        "admin_connected": record.admin_connected,
        "admin_disconnected": record.admin_disconnected,
        "in_progress": record.in_progress,
        "solved": record.solved,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": record_dict})

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send_json({"action": "send_message", "data": record_dict})


async def user_add_file_to_message(
        account_id: int,
        message_service: MessageService,
        item_id: int,
        file_uuid: str,
        file_name: str,
        file_size: int,
):
    account_ws, account = next(((ws, user) for ws, user in users_connections if user['id'] == account_id), None)
    company_id = account["company_id"]

    message = await message_service.get_by_id(item_id)
    if not message:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "add_file_to_message", "error": "Message not found"})
        return
    if message.user_id != account_id:
        for user_ws, user in users_connections:
            if user['id'] == account_id:
                await user_ws.send_json({"action": "add_file_to_message", "error": "Access denied"})
        return

    message_file = MessageFileCreate(
        item_id=item_id,
        file_uuid=file_uuid,
        file_name=file_name,
        file_size=file_size,
    )

    record = await message_service.add_file(message_file)

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send(json.dumps({"action": "add_file_to_message", "data": record}))

    for user_ws, user in users_connections:
        if user['id'] == account_id:
            await user_ws.send(json.dumps({"action": "add_file_to_message", "data": record}))


async def admin_connect_ticket(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        token: str,
        item_id: int,
):
    account_ws, account = next(((ws, admin) for ws, admin in admins_connections if admin['id'] == account_id), None)
    account_companies = account["companies"]
    account_companies_ids = [company['id'] for company in account_companies]

    ticket_old = await ticket_service.get_by_id(item_id)
    user = None
    if not ticket_old:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "connect_ticket", "error": "Ticket not found"})
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OAUTH_CHECK_URL}/users/{ticket_old.user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            user = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError, Exception):
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "connect_ticket", "error": "Cannot get user"})
        return

    company_id = user["company_id"]
    if user['company_id'] not in account_companies_ids:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "connect_ticket", "error": "Access denied"})

    ticket = TicketUpdate(
        title=ticket_old.title,
        description=ticket_old.description,
        status=ticket_old.status,
        user_id=ticket_old.user_id,
        admin_id=account_id,
    )

    record = await ticket_service.update(item_id, ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "connect_ticket", "data": record_dict})
    for user_ws, user in users_connections:
        if user['id'] == record.user_id:
            await user_ws.send_json({"action": "connect_ticket", "data": record_dict})

    message = MessageCreate(
        text='',
        user_id=user['id'],
        ticket_id=record.id,
        admin_id=account_id,
        admin_connected=True,
    )

    message_record = await message_service.create(message)

    message_record_dict = {
        "id": message_record.id,
        "text": message_record.text,
        "user_id": message_record.user_id,
        "admin_id": message_record.admin_id,
        "ticket_id": message_record.ticket_id,
        "admin_connected": message_record.admin_connected,
        "admin_disconnected": message_record.admin_disconnected,
        "in_progress": message_record.in_progress,
        "solved": message_record.solved,
        "created_at": message_record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": message_record_dict})
    for user_ws, user in users_connections:
        if user['id'] == message_record.user_id:
            await user_ws.send_json({"action": "send_message", "data": message_record_dict})


async def admin_disconnect_ticket(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        token: str,
        item_id: int,
):
    account_ws, account = next(((ws, admin) for ws, admin in admins_connections if admin['id'] == account_id), None)
    account_companies = account["companies"]
    account_companies_ids = [company['id'] for company in account_companies]

    ticket_old = await ticket_service.get_by_id(item_id)
    user = None
    if not ticket_old:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "disconnect_ticket", "error": "Ticket not found"})
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OAUTH_CHECK_URL}/users/{ticket_old.user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            user = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError, Exception):
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "disconnect_ticket", "error": "Cannot get user"})
        return

    company_id = user["company_id"]
    if user['company_id'] not in account_companies_ids:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "disconnect_ticket", "error": "Access denied"})

    ticket = TicketUpdate(
        title=ticket_old.title,
        description=ticket_old.description,
        status=ticket_old.status,
        user_id=ticket_old.user_id,
        admin_id=None,
    )

    record = await ticket_service.update(item_id, ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "disconnect_ticket", "data": record_dict})
    for user_ws, user in users_connections:
        if user['id'] == record.user_id:
            await user_ws.send_json({"action": "disconnect_ticket", "data": record_dict})

    message = MessageCreate(
        text='',
        user_id=user['id'],
        ticket_id=record.id,
        admin_id=account_id,
        admin_disconnected=True,
    )

    message_record = await message_service.create(message)

    message_record_dict = {
        "id": message_record.id,
        "text": message_record.text,
        "user_id": message_record.user_id,
        "admin_id": message_record.admin_id,
        "ticket_id": message_record.ticket_id,
        "admin_connected": message_record.admin_connected,
        "admin_disconnected": message_record.admin_disconnected,
        "in_progress": message_record.in_progress,
        "solved": message_record.solved,
        "created_at": message_record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": message_record_dict})
    for user_ws, user in users_connections:
        if user['id'] == message_record.user_id:
            await user_ws.send_json({"action": "send_message", "data": message_record_dict})


async def admin_set_ticket_status(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        token: str,
        item_id: int,
        status: int,
):
    account_ws, account = next(((ws, admin) for ws, admin in admins_connections if admin['id'] == account_id), None)
    account_companies = account["companies"]
    account_companies_ids = [company['id'] for company in account_companies]

    ticket_old = await ticket_service.get_by_id(item_id)
    if not ticket_old:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "set_ticket_status", "error": "Ticket not found"})
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OAUTH_CHECK_URL}/users/{ticket_old.user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            user = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError, Exception):
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "assign_ticket", "error": "Cannot get user"})
        return

    company_id = user["company_id"]
    if company_id not in account_companies_ids:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "set_ticket_status", "error": "Access denied"})
        return

    ticket = TicketUpdate(
        title=ticket_old.title,
        description=ticket_old.description,
        status=status,
        user_id=ticket_old.user_id,
        admin_id=ticket_old.admin_id,
    )

    record = await ticket_service.update(item_id, ticket)

    record_dict = {
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "set_ticket_status", "data": record_dict})
    for user_ws, user in users_connections:
        if user['id'] == record.user_id:
            await user_ws.send_json({"action": "set_ticket_status", "data": record_dict})

    match status:
        case 0:
            message = MessageCreate(
                text='',
                user_id=user['id'],
                ticket_id=record.id,
                admin_id=account_id,
            )
        case 1:
            message = MessageCreate(
                text='',
                user_id=user['id'],
                ticket_id=record.id,
                admin_id=account_id,
                in_progress=True,
            )
        case 2:
            message = MessageCreate(
                text='',
                user_id=user['id'],
                ticket_id=record.id,
                admin_id=account_id,
                solved=True,
            )
        case _:
            for admin_ws, admin in admins_connections:
                if admin['id'] == account_id:
                    await admin_ws.send_json({"action": "set_ticket_status", "error": "Unknown status"})
            return

    message_record = await message_service.create(message)

    message_record_dict = {
        "id": message_record.id,
        "text": message_record.text,
        "user_id": message_record.user_id,
        "admin_id": message_record.admin_id,
        "ticket_id": message_record.ticket_id,
        "admin_connected": message_record.admin_connected,
        "admin_disconnected": message_record.admin_disconnected,
        "in_progress": message_record.in_progress,
        "solved": message_record.solved,
        "created_at": message_record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": message_record_dict})
    for user_ws, user in users_connections:
        if user['id'] == message_record.user_id:
            await user_ws.send_json({"action": "send_message", "data": message_record_dict})


async def admin_send_message(
        account_id: int,
        ticket_service: TicketService,
        message_service: MessageService,
        token: str,
        text: str,
        user_id: int,
        ticket_id: int,
):
    account_ws, account = next(((ws, admin) for ws, admin in admins_connections if admin['id'] == account_id), None)
    account_companies = account["companies"]
    account_companies_ids = [company['id'] for company in account_companies]

    ticket_old = await ticket_service.get_by_id(ticket_id)
    if not ticket_old:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Ticket not found"})
        return
    user = None
    if not ticket_old:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Ticket not found"})
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OAUTH_CHECK_URL}/users/{ticket_old.user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            user = response.json()
    except httpx.HTTPStatusError as e:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Cannot get user"})
    except httpx.RequestError as e:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Cannot get user"})
    except Exception as e:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Cannot get user"})
    if not user:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Cannot get user"})

    company_id = user["company_id"]
    if user['company_id'] not in account_companies_ids:
        for admin_ws, admin in admins_connections:
            if admin['id'] == account_id:
                await admin_ws.send_json({"action": "send_message", "error": "Access denied"})

    message = MessageCreate(
        text=text,
        user_id=user_id,
        ticket_id=ticket_id,
        admin_id=account_id,
    )

    record = await message_service.create(message)

    record_dict = {
        "id": record.id,
        "text": record.text,
        "user_id": record.user_id,
        "admin_id": record.admin_id,
        "ticket_id": record.ticket_id,
        "admin_connected": record.admin_connected,
        "admin_disconnected": record.admin_disconnected,
        "in_progress": record.in_progress,
        "solved": record.solved,
        "created_at": record.created_at.isoformat(),
    }

    for admin_ws, admin in admins_connections:
        if company_id in {company['id'] for company in admin['companies']}:
            await admin_ws.send_json({"action": "send_message", "data": record_dict})
    for user_ws, user in users_connections:
        if user['id'] == record.user_id:
            await user_ws.send_json({"action": "send_message", "data": record_dict})


# async def admin_add_file_to_message(
#         account_id: int,
#         message_service: MessageService,
#         item_id: int,
#         file_uuid: str,
#         file_name: str,
#         file_size: int,
# ):
#     account_ws, account = next((ws, admin for ws, admin in admins_connections if admin['id'] == account_id), None)
#     account_companies = account["companies"]
#     account_companies_ids = [company['id'] for company in account_companies]
#
#     message = await message_service.get_by_id(item_id)
#     if not message:
#         for admin_ws, admin in admins_connections:
#             if admin['id'] == account_id:
#                 await admin_ws.send_json({"action": "add_file_to_message", "error": "Message not found"})
#         return
#
#     for user_ws, user in users_connections:
#         if user['id'] == message['user_id']:
#             company_id = user["company_id"]
#             if user.company_id not in account_companies_ids:
#                 for admin_ws, admin in admins_connections:
#                     if admin['id'] == account_id:
#                         await admin_ws.send_json({"action": "add_file_to_message", "error": "Access denied"})
#                 return
#
#     message_file = MessageFileCreate(
#         item_id=item_id,
#         file_uuid=file_uuid,
#         file_name=file_name,
#         file_size=file_size,
#     )
#
#     record = await message_service.add_file(message_file)
#
#     for admin_ws, admin in admins_connections:
#         if company_id in {company['id'] for company in admin['companies']}:
#             await admin_ws.send_json({"action": "add_file_to_message", "data": record})
#     for user_ws, user in users_connections:
#         if user['id'] == record.user_id:
#             await user_ws.send(json.dumps({"action": "add_file_to_message", "data": record}))
