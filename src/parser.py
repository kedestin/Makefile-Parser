#!/usr/lib/python3.6
# """
# Tested with GNU MAKE

#     $user: make --version
#     GNU Make 3.81
#     Copyright (C) 2006  Free Software Foundation, Inc.
#     This is free software; see the source for copying conditions.
#     There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A
#     PARTICULAR PURPOSE.

#     This program built for x86_64-pc-linux-gnu
# """

# NOTE
# Known Bugs/Issues
# * No attempt was made to handle escaped characters
# * Variables/functions of the form $(), ${} are only detected if they contain
#   balanced pairs of delimiters [() or {}]
# * ; is a valid character within a root level variable assignment, but
#   mkParseTree currently will not recognize it as such
# * Absolutely no static analysis is done; mkParseTree interprets makefiles as
#   written and makes no attempt to understand the implications of
#   variable/function substitution

# TODO
# ; doesn't seem to be legal within a target, but seems to be legal within a
#   root level variable declaration
#
# Add support for trailing comments
# TODO
# Rework Regexes given new entitylist definition
# TODO
# unittests: GTEST_LIB    + = /usr/lib
# Is a list of prerequisites
# NOTE
# mk rules must have prerequisites even, if empty
# The following is illegal since no prerequisites exist
# foo: bar=baz
#       echo $@
#

import regex
import difflib


class mkParseTree():
    """
        mkParseTree - A class that generates a simple parse tree for a given makefile
    """
    def __init__(self, makefile: str = None):
        self.tree = []
        self.context = mkParseTree.Context.ROOT
        if makefile is not None:
            self.parse(makefile)

    def __contains__(self, item):
        return item in self.tree

    def __iter__(self):
        return iter(self.tree)

    class Context():
        ROOT = 1
        RULE = 1 << 1
        RECIPE = 1 << 2

    def _update(self, cxt, newLine):
        def default_update(func):
            def toRun(tree, cxt, newLine):
                tree.append(newLine)
                func(tree, cxt, newLine)

            return toRun

        @default_update
        def variable_assignment(tree, cxt, newLine):
            pass

        @default_update
        def empty_line(tree, cxt, newLine):
            pass

        @default_update
        def comment(tree, cxt, newLine):
            pass

        @default_update
        def rule(tree, cxt, newLine):
            if "variable_assignment" in newLine.data:
                newLine.data["variable_assignment"] = mkStatement.fromLine(
                    newLine.data["variable_assignment"],
                    asStatement="variable_assignment"
                )
            if "recipe" in newLine.data:
                newLine.data["recipe"] = [
                    mkStatement.fromLine(
                        "\t" + newLine.data["recipe"], asStatement="recipe"
                    )
                ]
                # newLine.recipe = [mkStatement.fromLine("\t" + newLine.recipe, asStatement="recipe")]

        @default_update
        def recipe(tree, cxt, newLine):
            collector = []
            for x in reversed(tree):
                if x.name in ["empty_line", "comment", "recipe"]:
                    collector.append(tree.pop())
                elif x.name == "rule":
                    if "recipe" in x.data:
                        x.data["recipe"].extend(reversed(collector))
                    else:
                        x.data.update({"recipe": list(reversed(collector))})
                    break
                else:
                    raise ValueError

        locals()[newLine.name](self.tree, cxt, newLine)

    @staticmethod
    def removeLineContinuations(makefile: str):
        # All horizontal whitespace leading upto a '\' followed by a newline
        # and all following whitespace until first non whitespace character
        lineContinuation = regex.compile(
            r'[\t\p{Zs}]*\\\n[\t\p{Zs}]*', regex.MULTILINE
        )
        # The GNU make manual states that line continuations are replaced with
        # a single space
        return lineContinuation.sub(' ', makefile)

    def parse(self, makefile: str):
        # Transform all continued lines into a single line
        makefile = mkParseTree.removeLineContinuations(makefile)

        for line in regex.finditer('^.*$', makefile, regex.MULTILINE):
            newLine = mkStatement.fromLine(line.group(), context=self.context)
            if newLine:
                self._update(self.context, newLine)
            else:
                raise ValueError(line.group())
            if self.tree[-1].introducedContext is not None:
                self.context = self.tree[-1].introducedContext
        # for elem in self.tree: print(elem)



    def clear(self):
        self.__init__()

    def dumpMakefile(self):
        return '\n'.join(str(x) for x in self.tree)


class mkNone():
    """
        Analog for C#'s null conditional
        Is value equal to None, but is not reference equal to none
    """
    def __getattr__(self, attr):
        return self

    def __eq__(self, x):
        return x is None

    def __bool__(self):
        return bool(None)


class mkStatement():
    defines = r"""
    (?(DEFINE)
        # fn_ prefix denotes a subroutine
        # pre-Primitives
        #(?<fn_entityChars>[^\s:=#])
        (?<fn_entityChars>[^\s:=;#]) # For makefile rule draft
        # NOTE
        # \h = [\t\p{Zs}] = horizontalWhitespace
        # Primitives
        (?<fn_variableOrFunction>\$(?:(?<fn_all>\((?<fn_innerParens>[^(){}]+|(?&fn_all))*+\)|\{(?&fn_innerParens)*+\})|.))
        (?<fn_equals>(?:\+\=|\:(?:\:\=|\=)|\?\=|\=))
        (?<fn_comment>[\t\p{Zs}]*+\#.*+$)
        # Compound Primitives
        (?<fn_entity>(?:(?&fn_variableOrFunction)|(?&fn_entityChars))++)
        (?<fn_entityList>(?:(?&fn_entity)|[\t\p{Zs}]++)++)
        # (?<fn_entityList>(?&fn_entity)(?:[\t\p{Zs}]++(?&fn_entity))*)
        # Statements
        # (?<fn_variableAssign>(?&fn_entityList)(?&fn_equals))
        (?<fn_variableAssign>[\t\p{Zs}]*+(?&fn_entity)[\t\p{Zs}]*+(?&fn_equals))
    )
    """
    regexes = (
        # Order matters; first match is picked
        {
            "name":
                "rule",
            "pattern":
                r"""%(defines)s
                # List of entities, preceded by whitespace
                # (can't start with tab) is the target
                (?<target>^(?!\t)[\t\p{Zs}]*(?&fn_entityList))
                # Followed by a single or double colon
                (?<colon>(?!(?&fn_equals)):{1,2})
                # Optionally followed by either
                #   * A list of prerequisites optionally followed by
                #     recipe on same line
                #   * Or, a target/pattern specific variable assignment
                (?:
                    (?<prerequisites>(?&fn_entityList)(?:;|$)(?<recipe>.++)?)
                    | (?<variable_assignment>(?&fn_variableAssign)(?:(?:(?&fn_variableOrFunction)|.)++))
                )?
            """,
            "allowedIn":
                mkParseTree.Context.ROOT | mkParseTree.Context.RULE,
            "introducedContext":
                mkParseTree.Context.RULE,
        },
        {
            "name": "recipe",
            "pattern": r'%(defines)s^(?<recipe>\t.++)$',
            "allowedIn": mkParseTree.Context.RULE,
            "introducedContext": None,
        },
        {
            "name":
                "variable_assignment",
            "pattern":
                r"""%(defines)s
                # (?<variable>(?&fn_entityList))
                [\t\p{Zs}]*+
                (?<variable>(?&fn_entity))
                [\t\p{Zs}]*+
                (?<equals>(?&fn_equals))
                (?<value>.*+)
            """,
            "allowedIn":
                mkParseTree.Context.ROOT | mkParseTree.Context.RULE,
            "introducedContext":
                mkParseTree.Context.ROOT,
        },
        {
            "name": "empty_line",
            "pattern": r'(?<empty_line>^[\t\p{Zs}]*+$)',
            "allowedIn": mkParseTree.Context.ROOT | mkParseTree.Context.RULE,
            "introducedContext": None,
        },
        {
            "name": "comment",
            # "pattern": r'%(defines)s(?<comment>(?&fn_comment))',
            "pattern": r'[\t\p{Zs}]*+(?<hash>\#)(?<text>.*+$)',
            "allowedIn": mkParseTree.Context.ROOT | mkParseTree.Context.RULE,
            "introducedContext": None,
        },
    )
    for r, d in zip(
        regexes,
        len(regexes) * [regex.compile(defines, regex.VERBOSE).groupindex]
    ):
        r["pattern"] = regex.compile(
            r["pattern"] % {"defines": defines}, regex.VERBOSE
        )
        # This assumes non overlapping capture groups
        r["order"] = tuple(
            sorted(
                #  should be regex.compile(defines, regex.VERBOSE).groupindex
                set(r["pattern"].groupindex) - set(defines),
                key=r["pattern"].groupindex.get
            )
        )

    def fromLine(*args, asStatement=None, context=mkParseTree.Context.ROOT):
        self, line = args if len(args) == 2 else (
            mkStatement.__new__(mkStatement), *args
        )
        for r in mkStatement.regexes:
            a = asStatement is None
            b = r["name"] == asStatement
            c = bool(r["allowedIn"] & context)
            if not ((not a and b) or (a and c)):
                continue
            match = r["pattern"].match(line)
            if not match:
                continue
            self.metadata = r
            self.data = {
                k: v
                for k, v in match.groupdict().items() if v is not None
            }
            return self
        return mkNone()

    @staticmethod
    def d2s(dataDict, ordering):
        return ''.join(
            ('\n' + "\n".join(str(y) for y in dataDict[x])
            ) if type(dataDict[x]) is list else str(dataDict[x])
            for x in ordering if x in dataDict
        )

    def __init__(self, name, **kwargs):
        if not self.fromLine(
            mkStatement.d2s(
                kwargs,
                next(r for r in mkStatement.regexes if r["name"] == name
                    )["order"]
            ),
            asStatement=name
        ):
            raise ValueError

    def __getattr__(self, attr):
        if attr in self.metadata:
            return self.metadata[attr]
        elif attr in self.data:
            return self.data[attr]
        else:
            return mkNone()

    def __repr__(self):
        return mkStatement.d2s(self.data, self.order)


def main():
    with open('../tests/makefiles/testMakefile.mk', 'r') as toRead:
        makefile = toRead.read()
    mkAST = mkParseTree(makefile)
    print(mkAST.dumpMakefile())
    print(
        mkStatement.fromLine("CXX : asdasdasdasd").fromLine("CXX = asdasdasd")
    )
    print(
        mkStatement(
            "rule", target="CXX", colon=":", prerequisites="asdasdasdasd"
        )
    )


if __name__ == "__main__":
    main()
