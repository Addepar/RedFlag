import re
import json


class PullRequest:
    def __init__(self,
        repository,
        title,
        message,
        url,
        files,
        strip_lines=None,
        strip_html_comments=False,
    ):
        if not strip_lines:
            strip_lines = []
            
        self.__repository = repository
        self.__title = title
        self.__message = self._strip_lines(message, strip_lines, strip_html_comments)
        self.__url = url
        self.__files = files

    @property
    def repository(self) -> str:
        return self.__repository

    @repository.setter
    def repository(
        self,
        repository: str
    ) -> None:
        self.__repository = repository

    @property
    def title(self) -> str:
        return self.__title

    @title.setter
    def title(
        self,
        title: str
    ) -> None:
        self.__title = title

    @property
    def message(self) -> str:
        return self.__message

    @message.setter
    def message(
        self,
        message: str
    ) -> None:
        self.message = message

    @property
    def url(self) -> str:
        return self.__url

    @url.setter
    def url(
        self,
        url: str
    ) -> None:
        self.__url = url

    @property
    def files(self) -> list:
        return self.__files

    @files.setter
    def files(
        self,
        files: list
    ) -> None:
        self.__files = files

    @property
    def file_names(self) -> list:
        return [
            file.filename if file.__class__.__name__ == 'File' else file
            for file in self.__files
        ]

    @staticmethod
    def _strip_lines(message: str, lines: list, strip_html_comments: bool = False) -> str:
        for line in lines:
            message = message.replace(line, '')

        if strip_html_comments:
            re.sub(
                pattern='<!--.*?-->',
                repl='',
                string=message,
                flags=re.DOTALL
            )
        return message

    def to_dict(self) -> dict:
        dictionary = {}

        for key, value in vars(self).items():
            k = key.replace(f'_{self.__class__.__name__}__', '')

            if k == 'files':
                dictionary.update({'file_names': self.file_names})
            else:
                dictionary.update({k: value})
        
        return dictionary

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> object:
        if 'files' in data:
            files = data.get('files')
        else:
            files = data.get('file_names')
        return cls(
            repository=data.get('repository'),
            title=data.get('title'),
            message=data.get('message'),
            url=data.get('url'),
            files=files
        )
