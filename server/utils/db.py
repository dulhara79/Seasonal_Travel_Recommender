import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from server.utils.config import MONGODB_URI, MONGODB_DB

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    global client, db
    uri = MONGODB_URI or os.getenv("MONGODB_URI")
    name = MONGODB_DB or os.getenv("MONGODB_DB")
    if not uri or not name:
        raise RuntimeError("MONGODB_URI and MONGODB_DB must be set")

    client = AsyncIOMotorClient(uri)
    db = client[name]
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    # Ensure indexes for conversations collection to speed queries and
    # enforce lightweight constraints (e.g. many queries by user_id).
    # conversation documents will contain fields: user_id, session_id,
    # created_at, updated_at
    try:
        await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
        await db.conversations.create_index("session_id")
    except Exception:
        # Index creation should not crash startup; log and continue.
        print("Warning: could not ensure conversation indexes at startup.")
    # Avoid using non-ASCII emoji characters in logs to prevent
    # UnicodeEncodeError on Windows consoles using cp1252 encoding.
    print("Connected to MongoDB and ensured indexes were created.")


async def close_mongo_connection():
    global client, db
    if client:
        client.close()
        client = None
        db = None
        print("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    if db is None:
        raise RuntimeError("Database not connected. Call connect_to_mongo at startup.")

    return db