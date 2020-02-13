from parser import mkParseTree, mkStatement, mkNone
import regex
import subprocess


class mkAnalyser():

    entityMatcher = regex.compile(
        mkStatement.defines + "(?&fn_entity)", regex.VERBOSE
    )

    def __init__(self, pt: mkParseTree):
        p = subprocess.Popen(
            # Runs make, reads file from stdin, and dumps its database for
            # the given makefile
            ["make", "-f-", "-Bskp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        output, _ = p.communicate(pt.dumpMakefile().encode())
        p.wait()

        # This is a special makefile with the following properties
        # Each rule:
        #  * only has one target
        #  * only has a list of prerequisites
        #  * Variable updates are listed in comments
        # There is only 1 rule per target
        self.mkDataBase = mkParseTree(output.decode())

    def inferVariable(self, varName, *, atTarget=None):
        value = next(
            (
                variableDecl.value for variableDecl in self.mkDataBase.tree
                if variableDecl.variable == varName
            ), None
        )

        # Incorporate target specific updates if requested
        if atTarget is not None:
            targetRecipe = next(
                (x.recipe for x in self.mkDataBase if x.target == atTarget), []
            )
            for commentText in (cmt.text for cmt in targetRecipe if cmt.text):
                localUpdate = mkStatement.fromLine(
                    commentText, asStatement="variable_assignment"
                )
                if localUpdate.variable != varName:
                    continue

                if localUpdate.equals == "+=" and value is not None:
                    value = ' '.join([value, localUpdate.value])
                else:
                    value = localUpdate.value

        return value

    def inferPrerequisites(self, target):
        try:
            return mkAnalyser.entityMatcher.findall(
                next(
                    x.prerequisites
                    for x in self.mkDataBase.tree if x.target == target
                )
            )
        except StopIteration:
            return list()

    def dumpMakefile(self):
        return self.mkDataBase.dumpMakefile()


def main():
    with open('../tests/makefiles/testMakefile.mk', 'r') as toRead:
        makefile = toRead.read()
    mkAST = mkParseTree(makefile)

    # print(mkAnalyser(mkAST).mkDataBase.dumpMakefile())

    analyzer = mkAnalyser(mkAST)
    print(analyzer.mkDataBase.dumpMakefile())
    print("CXXFLAGS:", analyzer.inferVariable("CXXFLAGS"))
    print("CXXFLAGS at unittests:", analyzer.inferVariable("CXXFLAGS", atTarget="unittests"))
    print("unittests:", analyzer.inferPrerequisites('unittests'))   
    print("RayTracer++:", analyzer.inferPrerequisites('RayTracer++'))


if __name__ == "__main__":
    main()