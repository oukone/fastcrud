import uuid
import typing
import pydantic
from datetime import datetime
from fastapi import APIRouter
from fastcrud.storage import BaseStorage
from fastcrud.storage.local import LocalStorage
from fastcrud.utils import run_async_or_sync
from fastcrud.types import FilterOp


class BaseCrudModel(pydantic.BaseModel):
    uid: pydantic.UUID1 = pydantic.Field(default_factory=uuid.uuid1)
    created_on: datetime = pydantic.Field(default_factory=datetime.now)
    modify_on: datetime = pydantic.Field(default_factory=datetime.now)


class BaseCrud:
    def __init__(self, model: BaseCrudModel, storage: BaseStorage):
        self.model = model
        self.storage = storage

        async def get(uid: str):
            """
            Get an object by its unique id
            """
            return await run_async_or_sync(self._get, uid)

        async def get_many(field: str, value: str, opr: FilterOp = "eq"):
            """
            Get one or more objects by a comparison operator

            See: :func:`fastcrud.storage.local.default_filter` docstring
            for more details
            """
            return await run_async_or_sync(self._get_many, field, value, opr)

        async def create(obj: self.model):
            """
            Create an object, generating a unique id by default
            """
            return await run_async_or_sync(self._create, obj)

        async def create_many(objs: typing.List[self.model]):
            """
            Bulk insert a list of objects, generating unique id's for all of
            them by default
            """
            return await run_async_or_sync(self._create_many, objs)

        async def put(uid: str, obj: self.model):
            """
            Update an object by unique id
            """
            return await run_async_or_sync(self._put, uid, obj)

        async def put_many(objs: typing.List[self.model]):
            """
            Update a list of objects
            """
            return await run_async_or_sync(self._put_many, objs)

        async def patch(uid: str, obj: self.model):
            """
            Create or update an object, generating a unique id for new objects
            """
            return await run_async_or_sync(self._patch, uid, obj)

        async def patch_many(objs: typing.List[self.model]):
            """
            Create or update many objects, creating unique id's if it is a new
            object
            """
            return await run_async_or_sync(self._patch_many, objs)

        async def delete(uid: str):
            """
            Delete an object by unique id
            """
            return await run_async_or_sync(self._delete, uid)

        async def delete_many(uids: typing.List[str]):
            """
            Delete many objects by list of unique id's
            """
            return await run_async_or_sync(self._delete_many, uids)

        self.get = get
        self.put = put
        self.patch = patch
        self.create = create
        self.delete = delete
        self.get_many = get_many
        self.put_many = put_many
        self.patch_many = patch_many
        self.delete_many = delete_many

    async def _get(self, uid):
        return await run_async_or_sync(self.storage.get, uid)

    async def _get_many(self, field, value, opr="eq"):
        return await run_async_or_sync(
            self.storage.get_many, field, value, opr
        )

    async def _create(self, obj):
        return await run_async_or_sync(self.storage.create, obj)

    async def _create_many(self, objs):
        return [await self._create(obj) for obj in objs]

    async def _put(self, uid, obj):
        return await run_async_or_sync(self.storage.put, uid, obj)

    async def _put_many(self, objs):
        return [await self._put(obj) for obj in objs]

    async def _patch(self, uid, obj):
        return await run_async_or_sync(self.storage.patch, uid, obj)

    async def _patch_many(self, objs):
        return [await self._patch(obj) for obj in objs]

    async def _delete(self, uid):
        return await run_async_or_sync(self.storage.delete, uid)

    async def _delete_many(self, uids):
        return [await self._delete(uid) for uid in uids]


class CRUDRouter(APIRouter):
    def __init__(
        self,
        *args,
        crud_cls: BaseCrud = BaseCrud,
        model: BaseCrudModel = None,
        storage_cls: BaseStorage = LocalStorage,
        storage_settings: typing.Dict = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.model = model
        self.crud_cls = crud_cls
        self.storage_cls = storage_cls
        self.storage_settings = storage_settings or dict()
        self.storage = storage_cls(model, **self.storage_settings)

        self.on_startup.append(self.storage.start)
        self.on_shutdown.append(self.storage.stop)

        self.crud = self.crud_cls(self.model, self.storage)
        self.crud.get = self.get("/{oid}")(self.crud.get)
        self.crud.get_many = self.get("/")(self.crud.get_many)
        self.crud.create = self.post("/")(self.crud.create)
        self.crud.patch = self.patch("/{oid}")(self.crud.patch)
        self.crud.patch_many = self.patch("/")(self.crud.patch_many)
        self.crud.put = self.put("/{oid}")(self.crud.put)
        self.crud.put_many = self.put("/")(self.crud.put_many)
        self.crud.delete = self.delete("/{oid}")(self.crud.delete)
        self.crud.delete_many = self.delete("/")(self.crud.delete_many)

    @property
    def tag(self):
        return self.model.__name__

    @property
    def prefix(self):
        return f"/{self.tag}".lower()
