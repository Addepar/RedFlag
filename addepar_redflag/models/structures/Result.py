import json

from .PullRequest import PullRequest
from .Ticket import Ticket


class Result:
    def __init__(
        self,
        pr: PullRequest,
        ticket: Ticket = None
    ):
        self.__pr = pr
        self.__ticket = ticket

    @property
    def pr(self):
        return self.__pr

    @pr.setter
    def pr(
        self,
        pr
    ):
        self.__pr = pr

    @property
    def ticket(self):
        return self.__ticket

    @ticket.setter
    def ticket(
        self,
        ticket
    ):
        self.__ticket = ticket

    @property
    def token_count(self):
        return self.__token_count

    @token_count.setter
    def token_count(
        self,
        token_count
    ):
        self.__token_count = token_count

    @property
    def review(self):
        return self.__review

    @review.setter
    def review(
        self,
        review
    ):
        self.__review = review

    @property
    def test_plan(self):
        return self.__test_plan

    @test_plan.setter
    def test_plan(
        self,
        test_plan
    ):
        self.__test_plan = test_plan

    def to_dict(self) -> dict:
        dictionary = {}

        for key, value in vars(self).items():
            k = key.replace(
                f'_{self.__class__.__name__}__',
                ''
            )

            if value.__class__.__name__ in ['PullRequest', 'Ticket']:
                dictionary.update({k: value.to_dict()})
            elif value.__class__.__name__ in ['Review', 'TestPlan']:
                dictionary.update({k: value.dict()})
            else:
                dictionary.update({k: value})
        
        return dictionary

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> object:
        pr = PullRequest.from_dict(data.get('pr'))
        ticket = None

        if data.get('ticket'):
            ticket = Ticket.from_dict(data.get('ticket'))
        
        return cls(pr=pr, ticket=ticket)
