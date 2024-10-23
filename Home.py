import streamlit as st
import firebase_admin
from firebase_admin import auth, exceptions, credentials, initialize_app
import asyncio
import os
from httpx_oauth.clients.google import GoogleOAuth2
from dotenv import load_dotenv

st.set_page_config(layout="wide")

# Load environment variables from .env file
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate({
  "type": "service_account",
  "project_id": "fin-rag",
  "private_key_id": "81d28e871cd4d5f22aa502b354d9730f0b3fc2cd",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCVOgrmkgP8h/Vs\nP7vdmaMH+Qjmbl++815mmfM+ltdcTiLkxosgPFBWYhICbwFViRA0NEXZqj9zC2mw\nkNOprnm67oqLIWP7FwkIexdzW59FS9TGCcSUG/p7PL8RhyOtmnCaXxTiRFnJdiKd\nnPcrFKT9cYbRpGtGXq6c+Kk3bWUNrGMzQ7hIS39DMJLUj6iejD4lnIw1Z9zk+7uI\nDfuEuE/ljjyM59hoKjrY0T8WmtwKQqnjdtac3iN7MzshTGJQahfoj73AE9C6ao5p\nmLjb13aJjDa1iprz4lu3ewn+OnVSlXq98y3/nezza6Gezh55kdd4ukq7m9oFho+5\nke3xdT/xAgMBAAECggEAEyWTi3pVskZcOjZClmV68nAaG72IDG9GgAH7ILSS+mAj\ngFjB4Md3BAu+RXtVClK1S7V0oZUuDJv8xMUNsMUBundBOyZ0IR3ssJ62khHB8aQQ\nBL7xGZMuGYzgSSaemyI9624NYcDPsmvgIiVR3hWz27mqyOWrRqf/CIYBPurgNJeP\n064jYFgA8tQjN1OzfQ+5/B6bhYJRtiSCgXjga2dLljkWsNwx1TXTmDs7UcQgyCP0\nq2wU8UHGvBcH7Uah+sA/c95Gp6Z2weLPP9Ws71Q+ZRrHU64AJuwJWBF+HmFIKO2o\npiYOET0F8kElr/Hu6pz48808kE98/aBK3HccDHeEVwKBgQDF/hkpMWKncCjL2Sq8\nNfXnYdCGjrLGe06LvkzgFVXx50lAG4yEYz9pN6g/+19dg+V/bK7+7WAj89JEh1E2\ndndnir3xM9DkO5sPryGu5r+pW56ExGd+/dKIqODe07dHk1QPThuxmOGPoMn578wl\n6gRGMOC7vXFVeYWNsetzupxbmwKBgQDA8mShJgTBrR1XLUZC+9lucJr+FQ/tHxte\nqZvd+ZluSlv+j2s1iEI8L/08jY1H81jK8vhRn9o5VhOUKTq0oWQaPiKpwe0CEdLL\nSoTbf9tvG0AzbWfGry/mQQSGVHevT6R/dbTIfNNLJOv4lMVzvyKzjW3oMBFNAhaZ\nKs8j5xYpYwKBgCWXX/mVOdDml6hUfCut5xleVfQmRcUvhjM8F2Z4RpAeRKcaU+yS\n12hHu/ch5/JeZ4VxAiy+rwFEesiuFHpNtc//5J5WIzQiKQeqTa/iecNS9N7qV2gi\nEwYFYmSMOAEr9MrPHqzyhOj7Mz30DIOqUdNt1k1u44TCBNxpSnX3mVY/AoGAZwaG\n+Q1F6Oy5B/2i0M2N0kzKVfWFJYZApRFHqwVGCgAmkwydoF37kAvH2ndzAwJLXULT\nmTIT4h22IpzJPf4XZ3PaKm7kUQCXX/mQa2wgDXmtlEhM62hL2VTKR7f+mFucaHq/\nZ3ZPlIZIgdlefWmH6/wOvbY85rPAwVR8ep0/1iUCgYEAw7a3Ql6UHHK+808Bwte6\n4Dm7JNe/rxWSrEl8xyZAlCRj4yKixG1KnuEsLLTMiY2vffCqQuDXTqdc1Vm7o5CT\niiA8qArJDlKjrv2yhyDMj159K5q6BfpF/4cbWrjQplGjvKHhA4ra6IwSiTXtR2r1\ncGEr9C6yXhSqy2Yn02yA32Y=\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-un38r@fin-rag.iam.gserviceaccount.com",
  "client_id": "115273446604935719381",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-un38r%40fin-rag.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
})

# Initialize Firebase app only if not already initialized
try:
    initialize_app(cred)
except ValueError as e:
    print(f"Error initializing Firebase: {e}")

# Initialize Google OAuth2 client
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
redirect_url = "http://localhost:8501/"  # Your redirect URL

client = GoogleOAuth2(client_id=client_id, client_secret=client_secret)


st.session_state.email = ""


async def get_access_token(client: GoogleOAuth2, redirect_url: str, code: str):
    return await client.get_access_token(code, redirect_url)


async def get_email(client: GoogleOAuth2, token: str):
    user_id, user_email = await client.get_id_email(token)
    return user_id, user_email


def get_logged_in_user_email():
    try:
        query_params = st.query_params
        code = query_params.get("code")
        if code:
            token = asyncio.run(get_access_token(client, redirect_url, code))
            st.experimental_set_query_params()

            if token:
                user_id, user_email = asyncio.run(
                    get_email(client, token["access_token"])
                )
                if user_email:
                    try:
                        user = auth.get_user_by_email(user_email)
                    except exceptions.FirebaseError:
                        user = auth.create_user(email=user_email)
                    st.session_state.email = user.email
                    return user.email
        return None
    except:
        pass


def show_login_button():
    authorization_url = asyncio.run(
        client.get_authorization_url(
            redirect_url,
            scope=["email", "profile"],
            extras_params={"access_type": "offline"},
        )
    )
    st.markdown(
        f'<a href="{authorization_url}" target="_self">Login</a>',
        unsafe_allow_html=True,
    )
    get_logged_in_user_email()


def app():
    st.title("Welcome!")
    if not st.session_state.email:
        get_logged_in_user_email()
        if not st.session_state.email:
            show_login_button()

    if st.session_state.email:
        st.success(f"Successfully logged in as {st.session_state.email}!")
        st.write(st.session_state.email)
        if st.button("Logout", type="primary", key="logout_non_required"):
            st.session_state.email = ""
            st.rerun()


app()
