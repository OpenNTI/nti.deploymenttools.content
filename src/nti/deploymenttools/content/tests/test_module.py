#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import os
import shutil
import tempfile

from nti.deploymenttools.content import archive_directory

import unittest


class TestModule(unittest.TestCase):

    def test_archive_directory(self):
        source_path = os.path.dirname(__file__)
        tmpdir = tempfile.mkdtemp()
        archive_path = os.path.join(tmpdir, "archive.zip")
        try:
            archive_directory(source_path, archive_path)
            assert_that(os.path.exists(archive_path), is_(True))
        finally:
            shutil.rmtree(tmpdir, True)
