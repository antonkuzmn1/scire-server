from fastapi import APIRouter

router = APIRouter(tags=["files"])

# @router.post("/file", response_model=FileOut)
# async def upload_file(
#         file: UploadFile = File(...),
#         service: FileService = Depends(get_file_service),
#         user_data: dict = Depends(verify_token),
# ):
#     try:
#         return await service.save_upload_file(file, user_data["id"])
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"File upload failed: {str(e)}"
#         )
#
#
# @router.get("/file/{file_uuid}")
# async def download_file(
#         file_uuid: str,
#         service: FileService = Depends(get_file_service),
#         user_data: dict = Depends(verify_token)
# ):
#     try:
#         file_info = await service.verify_file_access(
#             file_uuid,
#             str(user_data["id"]),
#             roles=[user_data.get("role")]
#         )
#         file_path = await service.get_file_path(file_uuid)
#
#         if not file_path:
#             raise HTTPException(404, detail="File not found")
#
#         return FileResponse(
#             file_path,
#             filename=file_info.name,
#             headers={"Content-Length": str(file_info.size)}
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))
#
#
# @router.delete("/file/{file_uuid}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_file(
#     file_uuid: str,
#     service: FileService = Depends(get_file_service),
#     _: dict = require_roles(["owner"])
# ):
#     if not await service.delete_file(file_uuid):
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="File not found"
#         )
#
#
# @router.get("/file")
# async def get_all_files(
#     service: FileService = Depends(get_file_service),
#     _: dict = require_roles(["owner"])
# ):
#     try:
#         return await service.get_all_files()
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))
