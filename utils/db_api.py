from sqlalchemy import BigInteger, String, Column, Integer, Text, DateTime, ForeignKey, Table, select, insert
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import config

# --- 1. СУЩНОСТИ (Таблицы) ---
class Base(DeclarativeBase):
    pass

post_channels_association = Table(
    'post_channels',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
    Column('channel_id', Integer, ForeignKey('channels.id'), primary_key=True),
    Column('message_id', BigInteger, nullable=True) # <-- ВАЖНОЕ ПОЛЕ!
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    channel_telegram_id = Column(BigInteger, unique=True)
    title = Column(String)
    added_by = Column(BigInteger, ForeignKey('users.telegram_id'))

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    content = Column(Text)
    media_file_id = Column(String, nullable=True)
    media_type = Column(String, nullable=True)
    publish_date = Column(DateTime, nullable=True)
    delete_after_minutes = Column(Integer, nullable=True) # Хранит минуты
    status = Column(String, default="draft")
    
    target_channels = relationship("Channel", secondary=post_channels_association)

class Statistics(Base):
    __tablename__ = 'statistics'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    views_at_delete = Column(Integer, default=0)

# НОВАЯ ТАБЛИЦА
class Template(Base):
    __tablename__ = 'templates'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    name = Column(String)
    content = Column(Text, nullable=True)
    media_file_id = Column(String, nullable=True)
    media_type = Column(String, nullable=True)

# Настройка движка
engine = create_async_engine(f"sqlite+aiosqlite:///{config.DB_NAME}")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- 2. ФУНКЦИИ (Логика) ---

async def register_user(telegram_id: int, username: str):
    async with async_session() as session:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(query)
        if not result.scalar_one_or_none():
            session.add(User(telegram_id=telegram_id, username=username))
            await session.commit()
            return True
        return False

async def add_channel(user_id: int, channel_id: int, title: str):
    async with async_session() as session:
        query = select(Channel).where(Channel.channel_telegram_id == channel_id)
        result = await session.execute(query)
        if not result.scalar_one_or_none():
            session.add(Channel(channel_telegram_id=channel_id, title=title, added_by=user_id))
            await session.commit()
            return True
        return False

async def get_user_channels(user_id: int):
    async with async_session() as session:
        query = select(Channel).where(Channel.added_by == user_id)
        result = await session.execute(query)
        return result.scalars().all()

async def create_post_in_db(data: dict):
    async with async_session() as session:
        new_post = Post(
            user_id=data['user_id'],
            content=data.get('text'),
            media_file_id=data.get('media_id'),
            media_type=data.get('media_type'),
            publish_date=data['publish_date'],
            delete_after_minutes=data.get('delete_after'),
            status='scheduled'
        )
        session.add(new_post)
        await session.flush()
        
        for ch_id in data['channels']:
            await session.execute(
                insert(post_channels_association).values(
                    post_id=new_post.id,
                    channel_id=ch_id
                )
            )
        await session.commit()
        return new_post.id

async def get_post_for_sending(post_id: int):
    async with async_session() as session:
        query = (
            select(Post)
            .options(selectinload(Post.target_channels))
            .where(Post.id == post_id)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

async def update_post_status(post_id: int, status: str):
    async with async_session() as session:
        query = select(Post).where(Post.id == post_id)
        result = await session.execute(query)
        post = result.scalar_one_or_none()
        if post:
            post.status = status
            await session.commit()

async def get_all_posts_with_status(user_id: int, status: str):
    async with async_session() as session:
        query = (
            select(Post)
            .options(selectinload(Post.target_channels))
            .where(Post.user_id == user_id, Post.status == status)
        )
        result = await session.execute(query)
        return result.scalars().all()

async def delete_post_from_db(post_id: int):
    async with async_session() as session:
        query = select(Post).where(Post.id == post_id)
        result = await session.execute(query)
        post = result.scalar_one_or_none()
        if post:
            await session.delete(post)
            await session.commit()
            return True
        return False

async def create_template(user_id: int, name: str, content: str, media_id: str, media_type: str):
    """Создать шаблон"""
    async with async_session() as session:
        new_tpl = Template(
            user_id=user_id,
            name=name,
            content=content,
            media_file_id=media_id,
            media_type=media_type
        )
        session.add(new_tpl)
        await session.commit()

async def get_user_templates(user_id: int):
    """Получить список шаблонов юзера"""
    async with async_session() as session:
        query = select(Template).where(Template.user_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()

async def delete_template(tpl_id: int):
    """Удалить шаблон"""
    async with async_session() as session:
        query = select(Template).where(Template.id == tpl_id)
        result = await session.execute(query)
        tpl = result.scalar_one_or_none()
        if tpl:
            await session.delete(tpl)
            await session.commit()
            return True
        return False

import asyncio
from pyrogram import Client
import config # Импортируем наш конфиг

# Используем переменные из config.py
API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = config.SESSION_NAME

async def main():
    print("Начинаем процесс создания сессии для юзербота...")
    print("Вам потребуется ввести номер телефона, код из Telegram и, возможно, пароль 2FA.")
    
    # Client создаст файл сессии с именем, указанным в SESSION_NAME
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
        me = await app.get_me()
        print("-" * 30)
        print(f"✅ Сессия успешно создана для пользователя: {me.first_name}")
        print(f"   ID: {me.id}")
        print(f"   Username: @{me.username}")
        print("-" * 30)
        print(f"Файл '{SESSION_NAME}.session' был создан в папке проекта.")
        print("Этот скрипт больше запускать не нужно.")

if __name__ == "__main__":
    # Проверка, что API_ID и API_HASH не пустые
    if not API_ID or not API_HASH:
        print("❌ Ошибка: API_ID и/или API_HASH не указаны в вашем .env файле.")
        print("Пожалуйста, заполните их и попробуйте снова.")
    else:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"\n❌ Произошла ошибка во время создания сессии: {e}")

async def get_messages_for_post_parsing(post_id: int):
    """
    Возвращает список кортежей (channel_telegram_id, message_id) для конкретного поста.
    Это нужно, чтобы парсер знал, какие сообщения ему проверять.
    """
    async with async_session() as session:
        # Сложный запрос с JOIN для получения нужных данных
        query = (
            select(Channel.channel_telegram_id, post_channels_association.c.message_id)
            .join(Channel, post_channels_association.c.channel_id == Channel.id)
            .where(
                post_channels_association.c.post_id == post_id,
                post_channels_association.c.message_id.is_not(None)
            )
        )
        result = await session.execute(query)
        return result.all()

async def save_statistics(post_id: int, total_views: int):
    """Сохраняет итоговое количество просмотров в таблицу Statistics."""
    async with async_session() as session:
        # Проверим, нет ли уже записи для этого поста
        query = select(Statistics).where(Statistics.post_id == post_id)
        existing_stat = await session.execute(query)
        if existing_stat.scalar_one_or_none():
            print(f"Статистика для поста #{post_id} уже существует. Обновление не требуется.")
            return

        new_stat = Statistics(post_id=post_id, views_at_delete=total_views)
        session.add(new_stat)
        await session.commit()
        print(f"Статистика для поста #{post_id} сохранена: {total_views} просмотров.")

async def save_message_id(post_id: int, channel_db_id: int, message_id: int):
    """Обновляет запись в post_channels, добавляя message_id отправленного сообщения."""
    from sqlalchemy import update
    
    async with async_session() as session:
        stmt = (
            update(post_channels_association)
            .where(
                post_channels_association.c.post_id == post_id,
                post_channels_association.c.channel_id == channel_db_id
            )
            .values(message_id=message_id)
        )
        await session.execute(stmt)
        await session.commit()

async def update_or_create_statistics(post_id: int, views: int):
    """
    Обновляет запись статистики для поста, если она есть, или создает новую.
    Используется для сбора "живой" статистики.
    """
    async with async_session() as session:
        # Пытаемся найти существующую запись
        query = select(Statistics).where(Statistics.post_id == post_id)
        result = await session.execute(query)
        stat_record = result.scalar_one_or_none()

        if stat_record:
            # Если нашли - обновляем
            stat_record.views_at_delete = views
            print(f"[Статистика] Обновлены данные для поста #{post_id}: {views} просмотров.")
        else:
            # Если не нашли - создаем
            new_stat = Statistics(post_id=post_id, views_at_delete=views)
            session.add(new_stat)
            print(f"[Статистика] Созданы новые данные для поста #{post_id}: {views} просмотров.")
        
        await session.commit()