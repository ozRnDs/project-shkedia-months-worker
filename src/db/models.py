from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    token_header: str | None = None

    def get_token_as_header(self):
        if self.token_header:
            return {"Authorization": self.token_header}
        return {"Authorization": self.get_token_as_string()}
    
    def get_token_as_string(self):
        return self.token_type + " " + self.access_token
        
    @staticmethod
    def from_token_header(token_header: str):
        token_type = token_header.split(" ")[0]
        access_token = token_header.split(" ")[1]
        return Token(access_token=access_token, token_type=token_type, token_header=token_header)