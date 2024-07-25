
import bcrypt
import jwt
from datetime import datetime, timedelta
from config import SECRET_KEY


class UserService:
    def __init__(self, db):
        self.db = db

    async def create_user(self, username, password):
        existing_user = await self.db.conn.fetchrow(
            'SELECT id FROM users WHERE username = $1',
            username
        )

        if existing_user:
            await self.db.close()
            return {"error": "Username already exists"}, 400

        hashed_password = bcrypt.hashpw(password.encode(
            'utf-8'), bcrypt.gensalt()).decode('utf-8')
        await self.db.connect()
        user = await self.db.conn.fetchrow(
            '''
            INSERT INTO users (username, password) 
            VALUES ($1, $2) 
            RETURNING id, username
            ''',
            username, hashed_password
        )
        await self.db.close()
        return {
            'id': str(user['id']),
            'username': user['username']
        }, 201

    async def login_user(self, username, password):
        await self.db.connect()
        user = await self.db.conn.fetchrow(
            'SELECT password FROM users WHERE username = $1',
            username
        )
        await self.db.close()

        if user is None:
            return {
                'status': 'error',
                'message': 'ユーザーが見つかりませんでした'
            }, 404

        if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            token = jwt.encode({
                'username': username,
                'exp': datetime.now() + timedelta(days=1)
            }, SECRET_KEY, algorithm='HS256')
            return {
                'status': 'success',
                'token': token
            }, 200
        else:
            return {
                'status': 'error',
                'message': 'パスワードが違います'
            }, 401
