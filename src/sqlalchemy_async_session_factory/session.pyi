from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

def create_async_session_maker(
    engine: AsyncEngine,
    expire_on_commit: bool = ...,
    **kwargs: object,
) -> async_sessionmaker[AsyncSession]: ...
def create_session_dependency(
    session_maker: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]: ...
