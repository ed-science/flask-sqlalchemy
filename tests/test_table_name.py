import inspect

import pytest
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.declarative import declared_attr

from flask_sqlalchemy.model import camel_to_snake_case


@pytest.mark.parametrize(
    ("name", "expect"),
    [
        ("CamelCase", "camel_case"),
        ("Snake_case", "snake_case"),
        ("HTMLLayout", "html_layout"),
        ("LayoutHTML", "layout_html"),
        ("HTTP2Request", "http2_request"),
        ("ShoppingCartSession", "shopping_cart_session"),
        ("ABC", "abc"),
        ("PreABC", "pre_abc"),
        ("ABCPost", "abc_post"),
        ("PreABCPost", "pre_abc_post"),
        ("HTTP2RequestSession", "http2_request_session"),
        ("UserST4", "user_st4"),
        (
            "HTTP2ClientType3EncoderParametersSSE",
            "http2_client_type3_encoder_parameters_sse",
        ),
        (
            "LONGName4TestingCamelCase2snake_caseXYZ",
            "long_name4_testing_camel_case2snake_case_xyz",
        ),
        ("FooBarSSE2", "foo_bar_sse2"),
        ("AlarmMessageSS2SignalTransformer", "alarm_message_ss2_signal_transformer"),
        ("AstV2Node", "ast_v2_node"),
        ("HTTPResponseCodeXYZ", "http_response_code_xyz"),
        ("get2HTTPResponse123Code", "get2_http_response123_code"),
        # ("getHTTPresponseCode", "get_htt_presponse_code"),
        # ("__test__Method", "test___method"),
    ],
)
def test_camel_to_snake_case(name, expect):
    assert camel_to_snake_case(name) == expect


def test_name(db):
    class FOOBar(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class BazBar(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class Ham(db.Model):
        __tablename__ = "spam"
        id = db.Column(db.Integer, primary_key=True)

    assert FOOBar.__tablename__ == "foo_bar"
    assert BazBar.__tablename__ == "baz_bar"
    assert Ham.__tablename__ == "spam"


def test_single_name(db):
    """Single table inheritance should not set a new name."""

    class Duck(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class Mallard(Duck):
        pass

    assert "__tablename__" not in Mallard.__dict__
    assert Mallard.__tablename__ == "duck"


def test_joined_name(db):
    """Model has a separate primary key; it should set a new name."""

    class Duck(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class Donald(Duck):
        id = db.Column(db.Integer, db.ForeignKey(Duck.id), primary_key=True)

    assert Donald.__tablename__ == "donald"


def test_mixin_id(db):
    """Primary key provided by mixin should still allow model to set
    tablename.
    """

    class Base:
        id = db.Column(db.Integer, primary_key=True)

    class Duck(Base, db.Model):
        pass

    assert not hasattr(Base, "__tablename__")
    assert Duck.__tablename__ == "duck"


def test_mixin_attr(db):
    """A declared attr tablename will be used down multiple levels of
    inheritance.
    """

    class Mixin:
        @declared_attr
        def __tablename__(self):  # noqa: B902
            return self.__name__.upper()

    class Bird(Mixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class Duck(Bird):
        # object reference
        id = db.Column(db.ForeignKey(Bird.id), primary_key=True)

    class Mallard(Duck):
        # string reference
        id = db.Column(db.ForeignKey("DUCK.id"), primary_key=True)

    assert Bird.__tablename__ == "BIRD"
    assert Duck.__tablename__ == "DUCK"
    assert Mallard.__tablename__ == "MALLARD"


def test_abstract_name(db):
    """Abstract model should not set a name. Subclass should set a name."""

    class Base(db.Model):
        __abstract__ = True
        id = db.Column(db.Integer, primary_key=True)

    class Duck(Base):
        pass

    assert "__tablename__" not in Base.__dict__
    assert Duck.__tablename__ == "duck"


def test_complex_inheritance(db):
    """Joined table inheritance, but the new primary key is provided by a
    mixin, not directly on the class.
    """

    class Duck(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class IdMixin:
        @declared_attr
        def id(self):  # noqa: B902
            return db.Column(db.Integer, db.ForeignKey(Duck.id), primary_key=True)

    class RubberDuck(IdMixin, Duck):
        pass

    assert RubberDuck.__tablename__ == "rubber_duck"


def test_manual_name(db):
    """Setting a manual name prevents generation for the immediate model. A
    name is generated for joined but not single-table inheritance.
    """

    class Duck(db.Model):
        __tablename__ = "DUCK"
        id = db.Column(db.Integer, primary_key=True)
        type = db.Column(db.String)

        __mapper_args__ = {"polymorphic_on": type}

    class Daffy(Duck):
        id = db.Column(db.Integer, db.ForeignKey(Duck.id), primary_key=True)

        __mapper_args__ = {"polymorphic_identity": "Warner"}

    class Donald(Duck):
        __mapper_args__ = {"polymorphic_identity": "Disney"}

    assert Duck.__tablename__ == "DUCK"
    assert Daffy.__tablename__ == "daffy"
    assert "__tablename__" not in Donald.__dict__
    assert Donald.__tablename__ == "DUCK"
    # polymorphic condition for single-table query
    assert 'WHERE "DUCK".type' in str(Donald.query)


def test_primary_constraint(db):
    """Primary key will be picked up from table args."""

    class Duck(db.Model):
        id = db.Column(db.Integer)

        __table_args__ = (db.PrimaryKeyConstraint(id),)

    assert Duck.__table__ is not None
    assert Duck.__tablename__ == "duck"


def test_no_access_to_class_property(db):
    """Ensure the implementation doesn't access class properties or declared
    attrs while inspecting the unmapped model.
    """

    class class_property:
        def __init__(self, f):
            self.f = f

        def __get__(self, instance, owner):
            return self.f(owner)

    class Duck(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class ns:
        is_duck = False
        floats = False

    class Witch(Duck):
        @declared_attr
        def is_duck(self):
            # declared attrs will be accessed during mapper configuration,
            # but make sure they're not accessed before that
            info = inspect.getouterframes(inspect.currentframe())[2]
            assert info[3] != "_should_set_tablename"
            ns.is_duck = True

        @class_property
        def floats(self):
            ns.floats = True

    assert ns.is_duck
    assert not ns.floats


def test_metadata_has_table(db):
    user = db.Table("user", db.Column("id", db.Integer, primary_key=True))

    class User(db.Model):
        pass

    assert User.__table__ is user


def test_correct_error_for_no_primary_key(db):
    with pytest.raises(ArgumentError) as info:

        class User(db.Model):
            pass

    assert "could not assemble any primary key" in str(info.value)


def test_single_has_parent_table(db):
    class Duck(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class Call(Duck):
        pass

    assert Call.__table__ is Duck.__table__
    assert "__table__" not in Call.__dict__
