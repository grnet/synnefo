
from commissioning  import (Callpoint,
                            CanonifyException,
                            SpecifyException,
                            Specificator,
                            Nothing, Integer, Serial, Text, Bytes,
                            Tuple, ListOf, Dict, Args)

Context             =   Dict(classname='Context')

Command = Text  (
        classname       =   'Command',
        choices         =   (
                'CREATE',
                'READ',
                'UPDATE',
                'DELETE',
        )
)

Path = Text (
        classname   =   'Path',
        regex       =   '([a-zA-Z0-9_+/]|%[0-9a-fA-F]{2})+'
)

Contents = Bytes    (
        classname   =   'Contents',
        max_length  =   4096,
        default     =   None
)

Positive = Integer  (
        classname   =   'Positive',
        minimum     =   0
)

Offset = Integer  (
        classname   =   'Offset',
        minimum     =   0
)

DataSpec = Tuple    (
                        Offset,
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
        error       =   Text(max_length=256)
)


class FSCrudAPI(Specificator):

    def create  (
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return Serial

    def read    (
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return DataSpec

    def update  (
            self,
            context     =   Context,
            path        =   Path,
            dataspec    =   DataSpec
        ):

        return Serial

    def delete  (
            self,
            context     =   Context,
            path        =   Path
        ):

        return Serial

API_Spec = FSCrudAPI

