from typing import List

from langchain.pydantic_v1 import BaseModel, Field, validator

from ...util.llm import convert_to_string


class Review(BaseModel):
    result: bool = Field(
        description='True if your reasoning dictates that this pull request should be reviewed, otherwise false.'
    )
    reasoning: str = Field(
        description='The reasoning behind whether or not the PR should be reviewed. This should be a step-by-step explanation of your reasoning and how the answer was determined.'
    )
    files: List[str] = Field(
        description='A list of files, chosen from the file names provided, that contain code that should be reviewed. If "result" is false, this should be an empty list.'
    )
    _convert = validator(
        'reasoning',
        pre=True,
        allow_reuse=True
    )(convert_to_string)


class TestPlan(BaseModel):
    test_plan: str = Field(description='The test plan created.')
    reasoning: str = Field(
        description='The reasoning for creating the test plan. This should be a step-by-step explanation of your reasoning and how the answer was determined.'
    )
    _convert = validator(
        'test_plan',
        'reasoning',
        pre=True,
        allow_reuse=True
    )(convert_to_string)
