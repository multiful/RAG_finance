import asyncio
from app.core.database import get_db

async def check():
    db = get_db()
    res = db.table("sources").select("*").execute()
    print(f"Sources found: {len(res.data)}")
    for s in res.data:
        print(f"ID: {s['source_id']}, Name: {s['name']}, FID: {s['fid']} (type: {type(s['fid'])}), Base URL: {s['base_url']}")

if __name__ == "__main__":
    asyncio.run(check())
