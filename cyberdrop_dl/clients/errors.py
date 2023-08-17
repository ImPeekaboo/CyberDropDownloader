
class InvalidContentTypeFailure(Exception):
    """This error will be thrown when the content type isn't as expected"""
    def __init__(self, *, message: str = "Invalid content type"):
        self.message = message
        super().__init__(self.message)


class NoExtensionFailure(Exception):
    """This error will be thrown when no extension is given for a file"""
    def __init__(self, *, message: str = "Extension missing for file"):
        self.message = message
        super().__init__(self.message)


class DownloadFailure(Exception):
    """This error will be thrown when a download fails"""
    def __init__(self, status: int, message: str = "Something went wrong"):
        self.status = status
        self.message = message
        super().__init__(self.message)
        super().__init__(self.status)
