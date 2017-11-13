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
import zipfile
import tempfile

import fudge

from nti.deploymenttools.content import export_course
from nti.deploymenttools.content import import_course
from nti.deploymenttools.content import restore_course
from nti.deploymenttools.content import archive_directory
from nti.deploymenttools.content import upload_rendered_content
from nti.deploymenttools.content import download_rendered_content

import unittest


class TestModule(unittest.TestCase):

    def test_archive_directory(self):
        source_path = os.path.dirname(__file__)
        tmpdir = tempfile.mkdtemp()
        archive_path = os.path.join(tmpdir, "archive.zip")
        try:
            archive_directory(source_path, archive_path)
            assert_that(os.path.exists(archive_path), is_(True))
            assert_that(zipfile.is_zipfile(archive_path),
                        is_(True))
        finally:
            shutil.rmtree(tmpdir, True)

    @fudge.patch('nti.deploymenttools.content.requests')
    def test_download_rendered_content(self, mock_rq):
        path = os.path.join(os.path.dirname(__file__),
                            'data', 'content.zip')
        with open(path, 'rb') as fp:
            data = fp.read()
        response = (fudge.Fake().has_attr(status_code=200)
                    .expects('raise_for_status')
                    .expects('iter_content').returns([data]))
        mock_rq.provides('get').returns(response)

        tmpdir = tempfile.mkdtemp()
        ua_string = "NextThought Download Rendered Content Unit Test"
        try:
            archive = download_rendered_content("bleach", 'alpha.dev',
                                                'aizen', 'captain', ua_string,
                                                tmpdir)
            assert_that(os.path.exists(archive), is_(True))
            assert_that(zipfile.is_zipfile(archive),
                        is_(True))
        finally:
            shutil.rmtree(tmpdir, True)

    @fudge.patch('nti.deploymenttools.content.requests')
    def test_export_course(self, mock_rq):
        path = os.path.join(os.path.dirname(__file__),
                            'data', 'course.zip')
        with open(path, 'rb') as fp:
            data = fp.read()
        response = (fudge.Fake().has_attr(status_code=200)
                    .expects('raise_for_status')
                    .expects('iter_content').returns([data]))
        mock_rq.provides('get').returns(response)

        tmpdir = tempfile.mkdtemp()
        ua_string = "NextThought Export Course Unit Test"
        try:
            archive = export_course('tag:nextthought.com,2011-10:NTI-CourseInfo-Bleach',
                                    'alpha.dev', 'aizen', 'captain',
                                    ua_string, False, tmpdir)
            assert_that(os.path.exists(archive), is_(True))
            assert_that(zipfile.is_zipfile(archive),
                        is_(True))
        finally:
            shutil.rmtree(tmpdir, True)

    @fudge.patch('nti.deploymenttools.content.requests')
    def test_import_course(self, mock_rq):
        path = os.path.join(os.path.dirname(__file__),
                            'data', 'course.zip')
        response = (fudge.Fake().has_attr(status_code=200)
                    .expects('raise_for_status')
                    .expects('json').returns({'Class': 'Course'}))
        mock_rq.provides('post').returns(response)

        ua_string = "NextThought Import Course Unit Test"
        result = import_course(path, 'alpha.dev', 'aizen', 'captain',
                               'alpha.dev', 'Anime', 'Bleach', ua_string)
        assert_that(result, is_(dict))

    @fudge.patch('nti.deploymenttools.content.requests')
    def test_restore_course(self, mock_rq):
        path = os.path.join(os.path.dirname(__file__),
                            'data', 'course.zip')
        response = (fudge.Fake().has_attr(status_code=200)
                    .expects('raise_for_status')
                    .expects('json').returns({'Class': 'Course'}))
        mock_rq.provides('post').returns(response)

        ua_string = "NextThought Restore Course Unit Test"
        result = restore_course(path, 'alpha.dev', 'aizen', 'captain',
                                'tag:nextthought.com,2011-10:NTI-CourseInfo-Bleach',
                                ua_string)
        assert_that(result, is_(dict))

    @fudge.patch('nti.deploymenttools.content.requests')
    def test_upload_rendered_content(self, mock_rq):
        path = os.path.join(os.path.dirname(__file__),
                            'data', 'content.zip')
        response = (fudge.Fake().has_attr(status_code=200)
                    .expects('raise_for_status')
                    .expects('json').returns({'Class': 'ContentPackage'}))
        mock_rq.provides('post').returns(response)

        ua_string = "NextThought Upload Rendered Content Unit Test"
        result = upload_rendered_content(path, 'alpha.dev', 'aizen', 'captain',
                                         'alpha.dev', ua_string)
        assert_that(result, is_(dict))
