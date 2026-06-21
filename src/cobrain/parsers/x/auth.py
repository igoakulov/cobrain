from cobrain.config import get_x_config, set_x_config

X_OAUTH2_SCOPES = [
    "tweet.read",
    "users.read",
    "bookmark.read",
    "offline.access",
    "like.read",
]
X_OAUTH2_REDIRECT_URI = "http://127.0.0.1"


class OAuth2TokenManager:
    def __init__(self, authorization_code: str | None = None):
        x_config = get_x_config()
        self.client_id = x_config["x_oauth2_client_id"]
        self.client_secret = x_config["x_oauth2_client_secret"]
        self.access_token = x_config["x_oauth2_access_token"]
        self.refresh_token = x_config["x_oauth2_refresh_token"]
        self.pkce_verifier = x_config.get("x_oauth2_pkce_verifier", "")
        self.authorization_code = authorization_code

    def _save_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None:
        set_x_config(
            oauth2_access_token=access_token,
            oauth2_refresh_token=refresh_token,
        )
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Set x_oauth2_client_id and x_oauth2_client_secret in vault config. Use $VAR for env vars.",
            )

        if self.authorization_code and not self.access_token:
            return self._exchange_code()

        if self.access_token:
            return self.refresh_token_if_needed()

        if not self.authorization_code:
            self._start_auth_flow()
        raise RuntimeError("OAuth2 authorization required.")

    def refresh_token_if_needed(self) -> str:
        if not self.refresh_token:
            raise RuntimeError("OAuth2 authorization required.")

        try:
            from xdk.oauth2_auth import OAuth2PKCEAuth

            auth = OAuth2PKCEAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=X_OAUTH2_REDIRECT_URI,
                scope=X_OAUTH2_SCOPES,
                token={
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                },
            )
            tokens = auth.refresh_token()
            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token", self.refresh_token)
            self._save_tokens(
                access_token,
                refresh_token,
                tokens.get("expires_in", 7200),
            )
            return access_token
        except Exception as e:
            raise RuntimeError(str(e)) from e

    def _exchange_code(self) -> str:
        from xdk.oauth2_auth import OAuth2PKCEAuth

        # Use saved pkce_verifier - this MUST match what was used when user authorized
        auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=X_OAUTH2_REDIRECT_URI,
            scope=X_OAUTH2_SCOPES,
        )

        if self.pkce_verifier:
            auth.set_pkce_parameters(code_verifier=self.pkce_verifier)

        callback_url = f"{X_OAUTH2_REDIRECT_URI}/?code={self.authorization_code}"

        tokens = auth.fetch_token(authorization_response=callback_url)

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token", "")
        expires_in = tokens.get("expires_in", 7200)
        self._save_tokens(access_token, refresh_token, expires_in)
        set_x_config(oauth2_pkce_verifier="")
        return access_token

    def _start_auth_flow(self) -> None:
        from xdk.oauth2_auth import OAuth2PKCEAuth

        auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=X_OAUTH2_REDIRECT_URI,
            scope=X_OAUTH2_SCOPES,
        )
        auth_url = auth.get_authorization_url()
        code_verifier = auth.code_verifier or ""
        set_x_config(oauth2_pkce_verifier=code_verifier)
        print("\n=== OAuth2 Authorization Required ===")
        print("WARNING: Authorization code expires in 30 seconds - act immediately!")
        print("1. Visit this URL and authorize:")
        print(f"{auth_url}")
        print(
            "\n2. Copy code from redirect URL (value after ?code= and before &state=)",
        )
        print(f"Example: {X_OAUTH2_REDIRECT_URI}/?code=CODE&state=...")
        print("\n3. Repeat your command with --authorization-code CODE")
        raise RuntimeError("OAuth2 authorization required.")
