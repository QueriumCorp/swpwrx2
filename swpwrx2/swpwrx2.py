"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources
from django.utils import translation
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, String, Scope, Dict, Float, Boolean
from xblockutils.resources import ResourceLoader


#DEBUG=settings.ROVER_DEBUG
# DEBUG=False
DEBUG=True

class Swpwrx2(XBlock):
    """
    Provides a method for embedding a StepWise POWER problem V2 into OpenEdX
    """

    has_author_view = True # tells the xblock to not ignore the AuthorView
    has_score = True       # tells the xblock to not ignore the grade event
    show_in_read_only_mode = True # tells the xblock to let the instructor view the student's work (lms/djangoapps/courseware/masquerade.py)


    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # TO-DO: delete count, and define your own fields.

    q_id = String(help="Question ID", default="", scope=Scope.content)

    count = Integer(
        default=0, scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        Create primary view of the Swpwrx2, shown to students when viewing courses.
        """
        if context:
            pass  # TO-DO: do something based on the context.
        html = self.resource_string("static/html/swpwrx2student.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swpwrx2student.css"))

        # Add i18n js
        statici18n_js_url = self._get_statici18n_js_url()
        if statici18n_js_url:
            frag.add_javascript_url(self.runtime.local_resource_url(self, statici18n_js_url))

        frag.add_javascript(self.resource_string("static/js/src/swpwrx2student.js"))
        frag.initialize_js('Swpwrx2')
        return frag

    # TO-DO: change this handler to perform your own actions.  You may need more
    # than one handler, or you may not need any handlers at all.
    @XBlock.json_handler
    def increment_count(self, data, suffix=''):
        """
        Increments data. An example handler.
        """
        if suffix:
            pass  # TO-DO: Use the suffix when storing data.
        # Just to show data coming in...
        assert data['hello'] == 'world'

        self.count += 1
        return {"count": self.count}

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """Create canned scenario for display in the workbench."""
        return [
            ("Swpwrx2",
             """<swpwrx2/>
             """),
            ("Multiple Swpwrx2",
             """<vertical_demo>
                <swpwrx2/>
                <swpwrx2/>
                <swpwrx2/>
                </vertical_demo>
             """),
        ]

    def studio_view(self, context=None):
        if DEBUG: logger.info('SWPWRX2 studio_view() entered.')
        """
        The STUDIO view of the Swpwrx2 XBlock, shown to instructors
        when authoring courses.
        """
        html = self.resource_string("static/html/swpwrx2studio.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swpwrx2studio.css"))
        frag.add_javascript(self.resource_string("static/js/src/swpwrx2studio.js"))

        frag.initialize_js('Swpwrx2Studio')
        return frag


    def author_view(self, context=None):
        if DEBUG: logger.info('Swpwrx2 author_view() entered')
        """
        The AUTHOR view of the Swpwrx2 XBlock, shown to instructors
        when previewing courses.
        """
        html = self.resource_string("static/html/swpwrx2author.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swpwrx2author.css"))
        frag.add_javascript_url("//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_HTMLorMML")
        frag.add_javascript(self.resource_string("static/js/src/swpwrx2author.js"))

        if DEBUG: logger.info("Swpwrx2 author_view v={a}".format(a=self.q_definition))

        # tell author_view how many variants are defined
        variants = 1

        if DEBUG: logger.info("Swpwrx2 XBlock author_view variants={a}".format(a=variants))

        frag.initialize_js('Swpwrx2Author', variants)
        return frag

    @staticmethod
    def _get_statici18n_js_url():
        """
        Return the Javascript translation file for the currently selected language, if any.

        Defaults to English if available.
        """
        locale_code = translation.get_language()
        if locale_code is None:
            return None
        text_js = 'public/js/translations/{locale_code}/text.js'
        lang_code = locale_code.split('-')[0]
        for code in (locale_code, lang_code, 'en'):
            loader = ResourceLoader(__name__)
            if pkg_resources.resource_exists(
                    loader.module_name, text_js.format(locale_code=code)):
                return text_js.format(locale_code=code)
        return None

    @staticmethod
    def get_dummy():
        """
        Generate initial i18n with dummy method.
        """
        return translation.gettext_noop('Dummy')
