
from commissioning  import (Callpoint,
                            CanonifyException,
                            SpecifyException,
                            Specificator,
                            Nothing, Integer, String,
                            Tuple, ListOf, Dict, Args)

Context             =   Dict(classname='Context')

Command = String    (
        classname       =   'Command',
        choices         =   (
                'CREATE',
                'READ',
                'UPDATE',
                'DELETE',
        )
)

Path = String   (
        classname   =   'Path',
        regex       =   '([a-zA-Z_+/]|%[0-9a-fA-F]{2})+'
)

Contents = String   (
        classname   =   'Contents',
        max_length  =   4096,
        default     =   None
)

Positive = Integer  (
        classname   =   'Positive',
        minimum     =   0
)

DataSpec = Tuple    (
                        Positive,
                        Contents,

        classname   =   'DataSpec',
        default     =   None
)

CommisionSpec = Dict    (
        classname   =   'CommissionSpec',
        command     =   Command,
        path        =   Path,
        dataspec    =   DataSpec
)

PhysicalDescription = Dict  (
        classname   =   'PhysicalDescription',
        path        =   Path,
        dataspec    =   DataSpec
)

PhysicalState = Dict    (
        classname   =   'PhysicalState',
        path        =   Path,
        dataspec    =   DataSpec,
        retries     =   Positive,
        error       =   String(max_length=256)
)


class FSCrudAPI(Specificator):

    def create  (
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return Nothing

    def update	(
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return Nothing

    def read    (
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return DataSpec

    def delete  (
            self,
            context     =   Context,
            path        =   Path
        ):

        return Nothing

API_Spec = FSCrudAPI

