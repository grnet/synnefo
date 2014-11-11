# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
from django.test import TestCase
from selenium import selenium
from multiprocessing import Process
from time import sleep

class FunctionalCase(TestCase):
    """
    Functional tests for synnefo.ui using Selenium
    """

    def setUp(self):
        """Make the selenium connection"""
        TestCase.setUp(self)
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*firefox",
                                 "http://localhost:8000/")
        self.selenium.start()

    def tearDown(self):
        """Kill processes"""
        TestCase.tearDown(self)
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

    def test_wizard(self):
        sel = self.selenium
        sel.open("/")
        sel.wait_for_page_to_load("10000")
        self.failUnless(sel.is_text_present("machines"))
        sleep(2)
        sel.click("create")
        sel.click("small")
        sel.click("//div[@id='wizard']/div/div[1]/button[2]")
        sleep(2)
        sel.click("medium")
        sleep(2)
        try:
            self.assertEqual("2048", sel.get_value("ram-indicator"))
        except AssertionError, e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("2", sel.get_value("cpu-indicator"))
        except AssertionError, e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("40", sel.get_value("storage-indicator"))
        except AssertionError, e:
            self.verificationErrors.append(str(e))
        sleep(2)
        sel.click("//div[@id='wizard']/div/div[2]/button[2]")
        sleep(2)
        self.assertEqual("2", sel.get_text("machine_cpu-label"))
        self.assertEqual("2048", sel.get_text("machine_ram-label"))
        self.assertEqual("40", sel.get_text("machine_storage-label"))
        sel.click("start")
        sleep(2)
        try:
            self.failUnless(sel.is_text_present("Success"))
        except AssertionError, e:
            self.verificationErrors.append(str(e))

        #self.assertEqual("Success!",
        #                 sel.get_text("//div[@id='error-success']/h3"))
        #sel.click("//div[@id='error-success']/a")
        #try: self.failUnless(sel.is_text_present("My Debian Unstable server"))
        #except AssertionError, e: self.verificationErrors.append(str(e))
