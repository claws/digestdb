# This makefile has been created to help developers perform common actions.
# This makefile is self-documenting. All lines that begin with '# help:' are
# extracted by the 'make help' rule and rendered as a list of commands.
# Therefore you should attempt to maintain consistency between each rule and
# it's preceeding comment line.

.PHONY: help clean scrub test docs style style.fix dist check_types

# help:
# help: Makefile help
# help:

STYLE_EXCLUDE_LIST:=git status --porcelain --ignored | grep "!!" | grep ".py$$" | cut -d " " -f2 | tr "\n" ","
STYLE_MAX_LINE_LENGTH:=160
STYLE_PEP8_CMD:=pep8 --exclude=.git,doc,$(shell $(STYLE_EXCLUDE_LIST)) --ignore=E309,E402 --max-line-length=$(STYLE_MAX_LINE_LENGTH) digestdb tests


# help: help                           - display this makefile's help information
help:
	@grep "^# help\:" Makefile | sed 's/\# help\: *//'


# help: clean                          - clean only ignored files (leave untracked)
clean:
	@git clean -X -f -d


# help: scrub                          - clean *all* files (removes ignored *and* untracked)
scrub:
	@git clean -x -d -f


# help: test                           - run project tests
test:
	@python -m unittest discover -s tests -v


# help: docs                           - generate project documentation
docs:
	@cd doc && make html


# help: style                          - perform pep8 check
style:
	@$(STYLE_PEP8_CMD)

# help: style.fix                      - perform pep8 check with autopep8 fixes
style.fix:
	@# If there are no files to fix then autopep8 typically returns an error
	@# because it was not passed any files to work on. Use xargs -r to
	@# avoid this problem.
	@$(STYLE_PEP8_CMD) -q  | xargs -r autopep8 -i --max-line-length=$(STYLE_MAX_LINE_LENGTH)


# help: check_types                    - check type hint annotations
check_types:
	@MYPYPATH=$VIRTUAL_ENV/lib/python3.5/site-packages mypy -p digestdb -s



# help: dist                           - create a source distribution package
dist:
	@python setup.py sdist


# help: dist.upload                    - upload a source distribution package
dist.upload:
	@python setup.py sdist upload


# Keep these lines at the end of the file to retain nice help
# output formatting.
# help:

