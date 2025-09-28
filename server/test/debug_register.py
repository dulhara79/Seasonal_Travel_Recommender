import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
from server.utils.config import MONGODB_URI, MONGODB_DB

async def main():
    uri = MONGODB_URI or os.getenv('MONGODB_URI')
    name = MONGODB_DB or os.getenv('MONGODB_DB')
    print('MONGO URI set?', bool(uri), 'DB name:', name)
    if not uri or not name:
        raise RuntimeError('MONGODB_URI and MONGODB_DB must be set in server/.env or environment')
    client = AsyncIOMotorClient(uri)
    db = client[name]
    await db.users.create_index('email', unique=True)
    await db.users.create_index('username', unique=True)
    # clean up test user if exists
    await db.users.delete_many({'email': 'alice@example.com'})

    existing = await db.users.find_one({'$or': [{'email': 'alice@example.com'}, {'username': 'alice123'}]})
    print('existing before insert:', existing)

    doc = {
        'username': 'alice123',
        'name': 'Alice Example',
        'email': 'alice@example.com',
        'hashed_password': 'fakehash',
        'created_at': datetime.datetime.utcnow()
    }

    result = await db.users.insert_one(doc)
    print('inserted id:', result.inserted_id)
    created = await db.users.find_one({'_id': result.inserted_id})
    print('created doc:', created)
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
