#     Copyright 2016, Kay Hayen, mailto:kay.hayen@gmail.com
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
""" Node for constant expressions. Can be all common built-in types.

"""

from logging import warning

from nuitka.__past__ import iterItems, long, unicode  # pylint: disable=W0622
from nuitka.Constants import (
    getConstantIterationLength,
    isConstant,
    isHashable,
    isIndexConstant,
    isIterableConstant,
    isMutable,
    isNumberConstant
)
from nuitka.Options import isDebug

from .NodeBases import CompileTimeConstantExpressionMixin, NodeBase
from .NodeMakingHelpers import (
    makeRaiseExceptionReplacementExpression,
    wrapExpressionWithSideEffects
)


class ExpressionConstantRefBase(CompileTimeConstantExpressionMixin, NodeBase):
    user_provided = False

    def __init__(self, constant, source_ref, user_provided = False):
        NodeBase.__init__(self, source_ref = source_ref)
        CompileTimeConstantExpressionMixin.__init__(self)

        assert isConstant(constant), repr(constant)

        self.constant = constant

        # Memory saving method, have the attribute only where necessary.
        if user_provided:
            self.user_provided = user_provided

        if not user_provided and isDebug():
            try:
                size = len(constant)

                if type(constant) in (str, unicode):
                    max_size = 1000
                else:
                    max_size = 256

                if size > max_size:
                    warning(
                        "Too large constant (%s %d) encountered at %s.",
                        type(constant),
                        size,
                        source_ref.getAsString()
                    )
            except TypeError:
                pass


    def __repr__(self):
        return "<Node %s value %r at %s %s>" % (
            self.kind,
            self.constant,
            self.source_ref.getAsString(),
            self.user_provided
        )

    def getDetails(self):
        return {
            "constant"      : self.constant,
            "user_provided" : self.user_provided
        }

    def getDetailsForDisplay(self):
        result = self.getDetails()

        if "constant" in result:
            result["constant"] = repr(result["constant"])

        return result

    def getDetail(self):
        return repr(self.constant)

    @staticmethod
    def isExpressionConstantRef():
        return True

    def computeExpression(self, constraint_collection):
        # Cannot compute any further, this is already the best.
        return self, None, None

    def computeExpressionCall(self, call_node, call_args, call_kw,
                              constraint_collection):

        # The arguments don't matter. All constant values cannot be called, and
        # we just need to make and error out of that.
        new_node = wrapExpressionWithSideEffects(
            new_node     = makeRaiseExceptionReplacementExpression(
                expression      = self,
                exception_type  = "TypeError",
                exception_value = "'%s' object is not callable" % type(self.constant).__name__
            ),
            old_node     = call_node,
            side_effects = call_node.extractPreCallSideEffects()
        )

        constraint_collection.onExceptionRaiseExit(TypeError)

        return new_node, "new_raise", "Predicted call of constant value to exception raise."

    def getCompileTimeConstant(self):
        return self.constant

    getConstant = getCompileTimeConstant

    def isMutable(self):
        return isMutable(self.constant)

    def isKnownToBeHashable(self):
        return isHashable(self.constant)

    def isNumberConstant(self):
        return isNumberConstant(self.constant)

    def isIndexConstant(self):
        return isIndexConstant(self.constant)

    def isIndexable(self):
        return self.constant is None or self.isNumberConstant()

    def isKnownToBeIterable(self, count):
        if isIterableConstant(self.constant):
            return count is None or \
                   getConstantIterationLength(self.constant) == count
        else:
            return False

    def isKnownToBeIterableAtMin(self, count):
        length = self.getIterationLength()

        return length is not None and length >= count

    def canPredictIterationValues(self):
        return self.isKnownToBeIterable(None)

    def getIterationValue(self, count):
        assert count < len(self.constant)

        return makeConstantRefNode(
            constant   = self.constant[count],
            source_ref = self.source_ref
        )

    def getIterationValues(self):
        source_ref = self.getSourceReference()

        return tuple(
            makeConstantRefNode(
                constant      = value,
                source_ref    = source_ref,
                user_provided = self.user_provided
            )
            for value in
            self.constant
        )

    def isMapping(self):
        return type(self.constant) is dict

    def isMappingWithConstantStringKeys(self):
        assert self.isMapping()

        for key in self.constant:
            if type(key) not in (str, unicode):
                return False
        return True

    def getMappingPairs(self):
        assert self.isMapping()

        pairs = []

        source_ref = self.getSourceReference()

        for key, value in iterItems(self.constant):
            pairs.append(
                makeConstantRefNode(
                    constant   = key,
                    source_ref = source_ref
                ),
                makeConstantRefNode(
                    constant   = value,
                    source_ref = source_ref
                )
            )

        return pairs

    def getMappingStringKeyPairs(self):
        assert self.isMapping()

        pairs = []

        source_ref = self.getSourceReference()

        for key, value in iterItems(self.constant):
            pairs.append(
                (
                    key,
                    makeConstantRefNode(
                        constant   = value,
                        source_ref = source_ref
                    )
                )
            )

        return pairs


    def isBoolConstant(self):
        return type(self.constant) is bool

    def mayHaveSideEffects(self):
        # Constants have no side effects
        return False

    def extractSideEffects(self):
        # Constants have no side effects
        return ()

    def getIntegerValue(self):
        if self.isNumberConstant():
            return int(self.constant)
        else:
            return None

    def getStringValue(self):
        if self.isStringConstant():
            return self.constant
        else:
            return None

    def getIterationLength(self):
        if isIterableConstant(self.constant):
            return getConstantIterationLength(self.constant)
        else:
            return None

    def isIterableConstant(self):
        return isIterableConstant(self.constant)

    def isUnicodeConstant(self):
        return type(self.constant) is unicode

    def isStringConstant(self):
        return type(self.constant) is str

    def getStrValue(self):
        if type(self.constant) is str:
            # Nothing to do.
            return self
        else:
            try:
                return makeConstantRefNode(
                    constant      = str(self.constant),
                    user_provided = self.user_provided,
                    source_ref    = self.getSourceReference(),
                )
            except UnicodeEncodeError:
                # Unicode constants may not be possible to encode.
                return None

    def computeExpressionIter1(self, iter_node, constraint_collection):
        if type(self.constant) in (list, set, frozenset, dict):
            result = makeConstantRefNode(
                constant      = tuple(self.constant),
                user_provided = self.user_provided,
                source_ref    = self.getSourceReference()
            )

            self.replaceWith(result)

            return (
                iter_node,
                "new_constant", """\
Iteration over constant %s changed to tuple.""" % type(self.constant).__name__
            )

        if not isIterableConstant(self.constant):
            # Any exception may be raised.
            constraint_collection.onExceptionRaiseExit(TypeError)

        return iter_node, None, None

    def hasShapeDictionaryExact(self):
        return type(self.constant) is dict


class ExpressionConstantNoneRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_NONE_REF"

    def __init__(self, source_ref, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = None,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    def getDetails(self):
        return {}


class ExpressionConstantTrueRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_TRUE_REF"

    def __init__(self, source_ref, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = True,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    def getDetails(self):
        return {}


class ExpressionConstantFalseRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_FALSE_REF"

    def __init__(self, source_ref, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = False,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    def getDetails(self):
        return {}


class ExpressionConstantEllipsisRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_ELLIPSIS_REF"

    def __init__(self, source_ref, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = Ellipsis,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    def getDetails(self):
        return {}


class ExpressionConstantDictRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_DICT_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantDictRef():
        return True


class ExpressionConstantTupleRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_TUPLE_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantTupleRef():
        return True


class ExpressionConstantListRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_LIST_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantListRef():
        return True


class ExpressionConstantSetRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_SET_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantSetRef():
        return True


class ExpressionConstantIntRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_INT_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantIntRef():
        return True


class ExpressionConstantLongRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_LONG_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantLongRef():
        return True


class ExpressionConstantStrRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_STR_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantStrRef():
        return True


class ExpressionConstantUnicodeRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_UNICODE_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantUnicodeRef():
        return True


class ExpressionConstantBytesRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_BYTES_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantBytesRef():
        return True


class ExpressionConstantFloatRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_FLOAT_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantFloatRef():
        return True


class ExpressionConstantComplexRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_COMPLEX_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantComplexRef():
        return True


class ExpressionConstantSliceRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_SLICE_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantSliceRef():
        return True


class ExpressionConstantTypeRef(ExpressionConstantRefBase):
    kind = "EXPRESSION_CONSTANT_TYPE_REF"

    def __init__(self, source_ref, constant, user_provided = False):
        ExpressionConstantRefBase.__init__(
            self,
            constant      = constant,
            user_provided = user_provided,
            source_ref    = source_ref
        )

    @staticmethod
    def isExpressionConstantTypeRef():
        return True


the_empty_dict = {}

class ExpressionConstantDictEmptyRef(ExpressionConstantDictRef):
    kind = "EXPRESSION_CONSTANT_DICT_EMPTY_REF"

    def __init__(self, source_ref, user_provided = False):
        ExpressionConstantDictRef.__init__(
            self,
            constant      = the_empty_dict,
            user_provided = user_provided,
            source_ref    = source_ref
        )


def makeConstantRefNode(constant, source_ref, user_provided = False):
    # This is dispatching per constant value and types, every case
    # to be a return statement, pylint: disable=R0911,R0912

    # Dispatch based on constants first.
    if constant is None:
        return ExpressionConstantNoneRef(
            source_ref    = source_ref,
            user_provided = user_provided
        )
    elif constant is True:
        return ExpressionConstantTrueRef(
            source_ref    = source_ref,
            user_provided = user_provided
        )
    elif constant is False:
        return ExpressionConstantFalseRef(
            source_ref    = source_ref,
            user_provided = user_provided
        )
    elif constant is Ellipsis:
        return ExpressionConstantEllipsisRef(
            source_ref    = source_ref,
            user_provided = user_provided
        )
    else:
        # Next, dispatch based on type.
        constant_type = type(constant)

        if constant_type is int:
            return ExpressionConstantIntRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is str:
            return ExpressionConstantStrRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is float:
            return ExpressionConstantFloatRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is long:
            return ExpressionConstantLongRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is unicode:
            return ExpressionConstantUnicodeRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is bytes:
            return ExpressionConstantBytesRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is dict:
            if constant:
                return ExpressionConstantDictRef(
                    source_ref    = source_ref,
                    constant      = constant,
                    user_provided = user_provided
                )
            else:
                return ExpressionConstantDictEmptyRef(
                    source_ref    = source_ref,
                    user_provided = user_provided
                )
        elif constant_type is tuple:
            return ExpressionConstantTupleRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is list:
            return ExpressionConstantListRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is set:
            return ExpressionConstantSetRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is complex:
            return ExpressionConstantComplexRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is slice:
            return ExpressionConstantSliceRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        elif constant_type is type:
            return ExpressionConstantTypeRef(
                source_ref    = source_ref,
                constant      = constant,
                user_provided = user_provided
            )
        else:
            # Missing constant type, ought to not happen, please report.
            assert False, constant_type
