import json


class Ticket:
    def __init__(
        self,
        id,
        summary=None,
        description=None
    ):
        self.__id = id
        self.__summary = summary
        self.__description = description

    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(
        self,
        id: str
    ) -> None:
        self.__id = id

    @property
    def summary(self) -> str:
        return self.__summary

    @summary.setter
    def summary(
        self,
        summary: str
    ) -> None:
        self.__summary = summary

    @property
    def description(self) -> str:
        return self.__description

    @description.setter
    def description(
        self,
        description: str
    ) -> None:
        self.__description = description

    def to_dict(self) -> dict:
        return dict(
            (key.replace(f'_{self.__class__.__name__}__', ''), value)
            for key, value in vars(self).items()
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> object:
        return cls(
            id=data.get('id'),
            summary=data.get('summary'),
            description=data.get('description')
        )
