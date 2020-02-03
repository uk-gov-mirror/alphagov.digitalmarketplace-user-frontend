#!/bin/bash
#
# Check whether requirements*.in been changed without updating requirements*.txt
#
# We want to make sure that we are running `pip-compile` whenever we change our
# Python requirements.
#
# In this repo the requirements files are generated from `*.in` files. This
# script checks whether an in file has changed but the corresponding requirements
# file has not.
#
# Returns 1 if `pip-compile` needs to be run, otherwise 0


# Requirements files to check
REQUIREMENTS_FILES=${@:-requirements.txt requirements-dev.txt}

# Git reference to compare against
BASE_COMMIT=${BASE_COMMIT:-master}
HEAD_COMMIT=${HEAD_COMMIT:-HEAD}

# test_unchanged [FILE...]
# Return 1 if file(s) has changed relative to BASE_COMMIT, otherwise 0
test_unchanged() {
  git diff --quiet $BASE_COMMIT $HEAD_COMMIT -- $@
}

# Return filename for requirements file
requirements_infile() {
  echo ${1%%.txt}.in
}

# Return 1 if requirement infile has chaged but not requirement file,
# otherwise 0
test_requirements_file() {
  local requirements_file=$1
  if [ ! -f $requirements_file ]
  then
    return 0
  fi

  local infile=$(requirements_infile $requirements_file)

  test_unchanged $infile || (! test_unchanged $requirements_file)
}

status=0
for requirements_file in $REQUIREMENTS_FILES
do
  if ! test_requirements_file $requirements_file
  then
    >&2 echo "$(requirements_infile $requirements_file) has changed since $BASE_COMMIT but $requirements_file has not"
    status=1
  fi
done

if [ $status -ne 0 ]
then
  # we want to allow changes to infiles that don't affect the requirements file
  # the easiest way to do this is to run `pip-compile` and test the output
  >&2 echo 'Running `make freeze-requirements`...'
  make freeze-requirements > /dev/null 2>&1
  BASE_COMMIT=HEAD HEAD_COMMIT= test_unchanged $REQUIREMENTS_FILES
  status=$?
fi

if [ $status -ne 0 ]
then
  >&2 echo 'Requirements files require updating. Consider running `git commit' $REQUIREMENTS_FILES'`'
fi

exit $status
