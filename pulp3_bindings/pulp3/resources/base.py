"""Classes to use for base models
"""
from pydantic import BaseModel, validate_model


class Pulp3BaseModel(BaseModel):
    """Base Pulp3 model all resources should inherit from
    """

    def update(self, data: dict):
        """Adds supported for updating the fields in an existing
        model
        :param data: dict of key value paris to update in the model
        :type data: dict
        :return: self
        """

        # See https://github.com/pydantic/pydantic/discussions/3139
        values, fields, error = validate_model(self.__class__, data)
        if error:
            raise error

        for name in fields:
            setattr(self, name, values[name])

        return self
