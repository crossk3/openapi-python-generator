import pytest
from openapi_schema_pydantic import OpenAPI
from openapi_schema_pydantic import Reference
from openapi_schema_pydantic import Schema

from openapi_python_generator.language_converters.python.model_generator import (
    _generate_property_from_reference,
)
from openapi_python_generator.language_converters.python.model_generator import (
    _generate_property_from_schema,
)
from openapi_python_generator.language_converters.python.model_generator import (
    generate_models,
)
from openapi_python_generator.language_converters.python.model_generator import (
    type_converter,
)
from openapi_python_generator.models import Model
from openapi_python_generator.models import Property
from openapi_python_generator.models import TypeConversion


@pytest.mark.parametrize(
    "test_openapi_types,expected_python_types",
    [
        (
            Schema(type="string"),
            TypeConversion(original_type="string", converted_type="str"),
        ),
        (
            Schema(type="integer"),
            TypeConversion(original_type="integer", converted_type="int"),
        ),
        (
            Schema(type="number"),
            TypeConversion(original_type="number", converted_type="float"),
        ),
        (
            Schema(type="boolean"),
            TypeConversion(original_type="boolean", converted_type="bool"),
        ),
        (
            Schema(type="object"),
            TypeConversion(original_type="object", converted_type="Dict[str, Any]"),
        ),
        (
            Schema(type="array"),
            TypeConversion(original_type="array<unknown>", converted_type="List[Any]"),
        ),
        (
            Schema(type="array", items=Schema(type="string")),
            TypeConversion(original_type="array<string>", converted_type="List[str]"),
        ),
        (
            Schema(type="array", items=Reference(ref="#/components/schemas/test_name")),
            TypeConversion(
                original_type="array<test_name>",
                converted_type="List[test_name]",
                import_types=["test_name"],
            ),
        ),
        (
            Schema(type="null"),
            TypeConversion(original_type="null", converted_type="Any"),
        ),
    ],
)
def test_type_converter_simple(test_openapi_types, expected_python_types):
    assert type_converter(test_openapi_types, True) == expected_python_types
    assert (
        type_converter(test_openapi_types, False).converted_type
        == "Optional[" + expected_python_types.converted_type + "]"
    )


@pytest.mark.parametrize(
    "test_openapi_types,expected_python_types",
    [
        (["string", "integer"], "str,int"),
        (["string", "integer", "number"], "str,int,float"),
        (["string", "integer", "number", "boolean"], "str,int,float,bool"),
        (
            ["string", "integer", "number", "boolean", "array"],
            "str,int,float,bool,List[Any]",
        ),
    ],
)
def test_type_converter_of_type(test_openapi_types, expected_python_types):
    # Generate Schema object from test_openapi_types
    schema = Schema(allOf=[Schema(type=i) for i in test_openapi_types])

    assert (
        type_converter(schema, True).converted_type
        == "Tuple[" + expected_python_types + "]"
    )
    assert (
        type_converter(schema, False).converted_type
        == "Optional[Tuple[" + expected_python_types + "]]"
    )

    schema = Schema(oneOf=[Schema(type=i) for i in test_openapi_types])

    assert (
        type_converter(schema, True).converted_type
        == "Union[" + expected_python_types + "]"
    )
    assert (
        type_converter(schema, False).converted_type
        == "Optional[Union[" + expected_python_types + "]]"
    )

    schema = Schema(anyOf=[Schema(type=i) for i in test_openapi_types])

    assert (
        type_converter(schema, True).converted_type
        == "Union[" + expected_python_types + "]"
    )
    assert (
        type_converter(schema, False).converted_type
        == "Optional[Union[" + expected_python_types + "]]"
    )


def test_type_converter_exceptions():
    with pytest.raises(TypeError):
        type_converter(Schema(type="unknown"), True)

    with pytest.raises(TypeError):
        type_converter(Schema(type="array", items=Schema(type="unknown")), False)


@pytest.mark.parametrize(
    "test_name, test_schema, test_parent_schema, expected_property",
    [
        (
            "test_name",
            Schema(type="string"),
            Schema(type="object"),
            Property(
                name="test_name",
                type=TypeConversion(
                    original_type="string", converted_type="Optional[str]"
                ),
                required=False,
                default="None",
            ),
        ),
        (
            "test_name",
            Schema(type="string"),
            Schema(type="object", required=["test_name"]),
            Property(
                name="test_name",
                type=TypeConversion(original_type="string", converted_type="str"),
                required=True,
                imported_type=["test_name"],
            ),
        ),
    ],
)
def test_type_converter_property(
    test_name, test_schema, test_parent_schema, expected_property
):
    assert (
        _generate_property_from_schema(test_name, test_schema, test_parent_schema)
        == expected_property
    )


@pytest.mark.parametrize(
    "test_name, test_reference, parent_schema, expected_property",
    [
        (
            "test_name",
            Reference(ref="#/components/schemas/test_name"),
            Schema(type="object"),
            Property(
                name="test_name",
                type=TypeConversion(
                    original_type="#/components/schemas/test_name",
                    converted_type="Optional[test_name]",
                    import_types=["test_name"],
                ),
                required=False,
                default="None",
                import_type=["test_name"],
            ),
        ),
        (
            "test_name",
            Reference(ref="#/components/schemas/test_name"),
            Schema(type="object", required=["test_name"]),
            Property(
                name="test_name",
                type=TypeConversion(
                    original_type="#/components/schemas/test_name",
                    converted_type="test_name",
                    import_types=["test_name"],
                ),
                required=True,
                default=None,
                import_type=["test_name"],
            ),
        ),
    ],
)
def test_type_converter_property_reference(
    test_name, test_reference, parent_schema, expected_property
):
    assert (
        _generate_property_from_reference(test_name, test_reference, parent_schema)
        == expected_property
    )


def test_model_generation(model_data: OpenAPI):
    result = generate_models(model_data.components)  # type: ignore

    assert len(result) == len(model_data.components.schemas.keys())  # type: ignore
    for i in result:
        assert isinstance(i, Model)
        assert i.content is not None

        compile(i.content, "<string>", "exec")
