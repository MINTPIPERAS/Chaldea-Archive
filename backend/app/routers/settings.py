"""BYOK API 配置管理：CRUD + 测试连接。"""

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal, get_db
from ..models import ApiConfig
from ..schemas import ApiConfigIn, ApiConfigOut, TestConfigRequest

router = APIRouter(prefix="/api/settings/api-configs", tags=["settings"])


@router.get("", response_model=list[ApiConfigOut])
async def list_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiConfig).order_by(ApiConfig.id))
    return result.scalars().all()


async def _unset_default_except(session: AsyncSession, keep_id: int | None) -> None:
    stmt = update(ApiConfig).where(ApiConfig.is_default.is_(True)).values(is_default=False)
    if keep_id is not None:
        stmt = stmt.where(ApiConfig.id != keep_id)
    await session.execute(stmt)


@router.post("", response_model=ApiConfigOut, status_code=201)
async def create_config(body: ApiConfigIn, db: AsyncSession = Depends(get_db)):
    config = ApiConfig(**body.model_dump())
    db.add(config)
    await db.flush()
    if config.is_default:
        await _unset_default_except(db, keep_id=config.id)
    await db.commit()
    await db.refresh(config)
    return config


@router.put("/{config_id}", response_model=ApiConfigOut)
async def update_config(config_id: int, body: ApiConfigIn, db: AsyncSession = Depends(get_db)):
    config = await db.get(ApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    for field, value in body.model_dump().items():
        setattr(config, field, value)
    if config.is_default:
        await _unset_default_except(db, keep_id=config.id)
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=204)
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    config = await db.get(ApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    await db.delete(config)
    await db.commit()


@router.post("/test")
async def test_config(body: TestConfigRequest):
    kind, base_url, api_key = body.provider_kind, body.base_url, body.api_key
    if body.id is not None:
        async with SessionLocal() as db:
            config = await db.get(ApiConfig, body.id)
            if not config:
                raise HTTPException(status_code=404, detail="配置不存在")
            kind, base_url, api_key = config.provider_kind, config.base_url, config.api_key

    if kind == "mock":
        return {"ok": True, "message": "mock 配置始终可用", "models": []}
    try:
        client = AsyncOpenAI(api_key=api_key or "", base_url=base_url or None, timeout=15)
        result = await client.models.list()
        names = [m.id for m in result.data][:50]
        return {"ok": True, "message": f"连接成功，发现 {len(names)} 个模型", "models": names}
    except Exception as exc:
        return {"ok": False, "message": f"连接失败：{exc}", "models": []}
