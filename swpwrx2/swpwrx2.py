"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources
import random
import json
import re
from logging import getLogger

from django.conf import settings
from django.utils import translation

from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, String, Scope, Dict, Float, Boolean
from xblock.utils.resources import ResourceLoader
from xblock.scorable import ScorableXBlockMixin, Score
from xblock.utils.studio_editable import StudioEditableXBlockMixin
from lms.djangoapps.courseware.courses import get_course_by_id

from django.utils import translation

UNSET = object()

logger = getLogger(__name__)

#DEBUG=settings.ROVER_DEBUG
# DEBUG=False
DEBUG=True

DEFAULT_RANK="cadet"  # What we'll use for a rank if not modified by the user/default
TEST_MODE=False

@XBlock.wants('user')
class Swpwrx2(StudioEditableXBlockMixin, ScorableXBlockMixin,XBlock):
    """
    Provides a method for embedding a StepWise POWER problem V2 into OpenEdX
    """

    has_author_view = True # tells the xblock to not ignore the AuthorView
    has_score = True       # tells the xblock to not ignore the grade event
    show_in_read_only_mode = True # tells the xblock to let the instructor view the student's work (lms/djangoapps/courseware/masquerade.py)

    MAX_VARIANTS = 1    # This code handles 1 variant

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # Place to store the UUID for this xblock instance.  Not currently displayed in any view.
    url_name = String(display_name="URL name", default='NONE', scope=Scope.content)

    # PER-QUESTION GRADING OPTIONS (SEPARATE SET FOR COURSE DEFAULTS)
    q_weight = Float(
        display_name="Problem Weight",
        help="Defines the number of points the problem is worth.",
        scope=Scope.content,
        default=1.0,
        enforce_type=True
    )

    q_id = String(help="Question ID", default="", scope=Scope.content)

    count = Integer(
        default=0, scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )

    q_grade_showme_ded = Float(display_name="Point deduction for using Show Solution",help="SWPWR Raw points deducted from 3.0 (Default: 3.0)", default=3.0, scope=Scope.content)
    q_grade_hints_count = Integer(help="SWPWR Number of Hints before deduction", default=2, scope=Scope.content)
    q_grade_hints_ded = Float(help="SWPWR Point deduction for using excessive Hints", default=1.0, scope=Scope.content)
    q_grade_errors_count = Integer(help="SWPWR Number of Errors before deduction", default=2, scope=Scope.content)
    q_grade_errors_ded = Float(help="SWPWR Point deduction for excessive Errors", default=1.0, scope=Scope.content)
    q_grade_min_steps_count = Integer(help="SWPWR Minimum valid steps in solution for full credit", default=3, scope=Scope.content)
    q_grade_min_steps_ded = Float(help="SWPWR Point deduction for fewer than minimum valid steps", default=0.25, scope=Scope.content)
    q_grade_app_key = String(help="SWPWR question app key", default="SBIRPhase2", scope=Scope.content);

    # PER-QUESTION HINTS/SHOW SOLUTION OPTIONS
    q_option_hint = Boolean(help='SWPWR Display Hint button if "True"', default=True, scope=Scope.content)
    q_option_showme = Boolean(help='SWPWR Display ShowSolution button if "True"', default=True, scope=Scope.content)

    # MAX ATTEMPTS PER-QUESTION OVERRIDE OF COURSE DEFAULT
    q_max_attempts = Integer(help="SWPWR Max question attempts (-1 = Use Course Default)", default=-1, scope=Scope.content)

    # STEP-WISE QUESTION DEFINITION FIELDS FOR VARIANTS
    display_name = String(display_name="SWPWR Display name", default='SWPWR', scope=Scope.content)

    q_id = String(help="Question ID", default="", scope=Scope.content)
    q_label = String(help="SWPWR Question label", default="", scope=Scope.content)
    q_stimulus = String(help="SWPWR Stimulus", default='Solve for \\(a\\). \\(5a+4=2a-5\\)', scope=Scope.content)
    q_definition = String(help="SWPWR Definition", default='SolveFor[5a+4=2a-5,a]', scope=Scope.content)
    q_type = String(help="SWPWR Type", default='gradeBasicAlgebra', scope=Scope.content)
    q_display_math = String(help="SWPWR Display Math", default='\\(\\)', scope=Scope.content)
    q_hint1 = String(help="SWPWR First Math Hint", default='', scope=Scope.content)
    q_hint2 = String(help="SWPWR Second Math Hint", default='', scope=Scope.content)
    q_hint3 = String(help="SWPWR Third Math Hint", default='', scope=Scope.content)
    q_swpwr_problem = String(help="SWPWR SWPWR Problem", default='', scope=Scope.content)
    # Invalid schema choices should be a CSV list of one or more of these: "TOTAL", "DIFFERENCE", "CHANGEINCREASE", "CHANGEDECREASE", "EQUALGROUPS", and "COMPARE"
    # Invalid schema choices can also be the official names: "additiveTotalSchema", "additiveDifferenceSchema", "additiveChangeSchema", "subtractiveChangeSchema", "multiplicativeEqualGroupsSchema", and "multiplicativeCompareSchema"
    # This Xblock converts the upper-case names to the official names when constructing the launch code for the React app, so you can mix these names.
    # Note that this code doesn't validate these schema names, so Caveat Utilitor.
    q_swpwr_invalid_schemas = String(display_name="Comma-separated list of unallowed schema names", help="SWPWR Comma-seprated list of unallowed schema names", default="",scope=Scope.content)
    # Rank choices should be "newb" or "cadet" or "learner" or "ranger"
    q_swpwr_rank = String(display_name="Student rank for this question", help="SWPWR Student rank for this question", default=DEFAULT_RANK, scope=Scope.content)
    q_swpwr_problem_hints = String(display_name="Problem-specific hints (JSON)", help="SWPWR optional problem-specific hints (JSON)", default="[]", scope=Scope.content)
    # STUDENT'S QUESTION PERFORMANCE FIELDS
    swpwr_results = String(help="SWPWR The student's SWPWR Solution structure", default="", scope=Scope.user_state)

    xb_user_email = String(help="SWPWR The user's email addr", default="", scope=Scope.user_state)
    grade = Float(help="SWPWR The student's grade", default=-1, scope=Scope.user_state)
    solution = Dict(help="SWPWR The student's last stepwise solution", default={}, scope=Scope.user_state)
    question = Dict(help="SWPWR The student's current stepwise question", default={}, scope=Scope.user_state)
    # count_attempts keeps track of the number of attempts of this question by this student so we can
    # compare to course.max_attempts which is inherited as an per-question setting or a course-wide setting.
    count_attempts = Integer(help="SWPWR Counted number of questions attempts", default=0, scope=Scope.user_state)
    raw_possible = Float(help="SWPWR Number of possible points", default=3,scope=Scope.user_state)
    # The following 'weight' is examined by the standard scoring code, so needs to be set once we determine which weight value to use
    # (per-Q or per-course). Also used in rescoring by override_score_module_state.
    weight = Float(help="SWPWR Defines the number of points the problem is worth.", default=1, scope=Scope.user_state)

    my_weight  = Integer(help="SWPWR Remember weight course setting vs question setting", default=-1, scope=Scope.user_state)
    my_max_attempts  = Integer(help="SWPWR Remember max_attempts course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_showme  = Integer(help="SWPWR Remember option_showme course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_hint  = Integer(help="SWPWR Remember option_hint course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_showme_ded  = Integer(help="SWPWR Remember grade_showme_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_count  = Integer(help="SWPWR Remember grade_hints_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_ded  = Integer(help="SWPWR Remember grade_hints_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_count  = Integer(help="SWPWR Remember grade_errors_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_ded  = Integer(help="SWPWR Remember grade_errors_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_count  = Integer(help="SWPWR Remember grade_min_steps_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_ded  = Integer(help="SWPWR Remember grade_min_steps_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_app_key  = String(help="SWPWR Remember app_key course setting vs question setting", default="", scope=Scope.user_state)

    # variant_attempted: Remembers the set of variant q_index values the student has already attempted.
    # We can't add a Set to Scope.user_state, or we get get runtime errors whenever we update this field:
    #      variants_attempted = Set(scope=Scope.user_state)
    #      TypeError: Object of type set is not JSON serializable
    # See e.g. this:  https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets
    # So we'll leave the variants in an Integer field and fiddle the bits ourselves :-(
    # We define our own bitwise utility functions below: bit_count_ones() bit_is_set() bit_is_set()

    variants_attempted = Integer(help="SWPWR Bitmap of attempted variants", default=0,scope=Scope.user_state)
    variants_count = Integer(help="SWPWR Count of available variants", default=0,scope=Scope.user_state)
    previous_variant = Integer(help="SWPWR Index (q_index) of the last variant used", default=-1,scope=Scope.user_state)

    # FIELDS FOR THE ScorableXBlockMixin

    is_answered = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if successfully answered'
    )

    correct = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if correctly answered'
    )

    raw_earned = Float(
        help="SWPWR Keeps maximum score achieved by student as a raw value between 0 and 1.",
        scope=Scope.user_state,
        default=0,
        enforce_type=True,
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The STUDENT view of the SWPWRXBlock, shown to students
        when viewing courses.  We set up the question parameters (referring to course-wide settings), then launch
        the javascript StepWise client.
        """

        if context:
            pass  # TO-DO: do something based on the context.

        if DEBUG: logger.info('SWPWRXBlock student_view() entered. context={context}'.format(context=context))

        if DEBUG: logger.info("SWPWRXBlock student_view() self={a}".format(a=self))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.runtime={a}".format(a=self.runtime))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.runtime.course_id={a}".format(a=self.runtime.course_id))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.previous_variant={v}".format(v=self.previous_variant))

        course = get_course_by_id(self.runtime.course_id)
        if DEBUG: logger.info("SWPWRXBlock student_view() course={c}".format(c=course))

        if DEBUG: logger.info("SWPWRXBlock student_view() q_max_attempts={b}".format(b=self.q_max_attempts))

        # NOTE: Can't set a self.q_* field here if an older imported swpwrxblock doesn't define this field, since it defaults to None
        # (read only?) so we'll use instance vars my_* to remember whether to use the course-wide setting or the per-question setting.
        # Similarly, some old courses may not define the stepwise advanced settings we want, so we create local variables for them.

        # For per-xblock settings
        temp_weight = -1
        temp_max_attempts = -1
        temp_option_hint = -1
        temp_option_showme = -1
        temp_grade_shome_ded = -1
        temp_grade_hints_count = -1
        temp_grade_hints_ded = -1
        temp_grade_errors_count = -1
        temp_grade_errors_ded = -1
        temp_grade_min_steps_count = -1
        temp_grade_min_steps_ded = -1
        temp_grade_app_key = ""

        # For course-wide settings
        temp_course_stepwise_weight = -1
        temp_course_stepwise_max_attempts = -1
        temp_course_stepwise_option_hint = -1
        temp_course_stepwise_option_showme = -1
        temp_course_stepwise_grade_showme_ded = -1
        temp_course_stepwise_grade_hints_count = -1
        temp_course_stepwise_grade_hints_ded = -1
        temp_course_stepwise_grade_errors_count = -1
        temp_course_stepwise_grade_errors_ded = -1
        temp_course_stepwise_grade_min_steps_count = -1
        temp_course_stepwise_grade_min_steps_ded = -1
        temp_course_stepwise_grade_app_key = ""

        # Defaults For course-wide settings if they aren't defined for this course
        def_course_stepwise_weight = 1.0
        def_course_stepwise_max_attempts = None
        def_course_stepwise_option_hint = True
        def_course_stepwise_option_showme = True
        def_course_stepwise_grade_showme_ded = 3.0
        def_course_stepwise_grade_hints_count = 2
        def_course_stepwise_grade_hints_ded = 1.0
        def_course_stepwise_grade_errors_count = 2
        def_course_stepwise_grade_errors_ded = 1.0
        def_course_stepwise_grade_min_steps_count = 3
        def_course_stepwise_grade_min_steps_ded = 0.25
        def_course_stepwise_grade_app_key = "SBIRPhase2"

        # after application of course-wide settings
        self.my_weight = -1
        self.my_max_attempts = -1
        self.my_option_showme = -1
        self.my_option_hint = -1
        self.my_grade_showme_ded = -1
        self.my_grade_hints_count = -1
        self.my_grade_hints_ded = -1
        self.my_grade_errors_count = -1
        self.my_grade_errors_ded = -1
        self.my_grade_min_steps_count = -1
        self.my_grade_min_steps_ded = -1
        self.my_grade_app_key = ""

        # Fetch the xblock-specific settings if they exist, otherwise create a default


        try:
            temp_weight = self.q_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_weight was not defined in this instance: {e}'.format(e=e))
            temp_weight = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_weight: {t}'.format(t=temp_weight))

        try:
            temp_max_attempts = self.q_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_max_attempts = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_max_attempts: {t}'.format(t=temp_max_attempts))

        try:
            temp_option_hint = self.q_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.option_hint was not defined in this instance: {e}'.format(e=e))
            temp_option_hint = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_option_hint: {t}'.format(t=temp_option_hint))

        try:
            temp_option_showme = self.q_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.option_showme was not defined in this instance: {e}'.format(e=e))
            temp_option_showme = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_option_showme: {t}'.format(t=temp_option_showme))

        try:
            temp_grade_showme_ded = self.q_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_showme_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_showme_ded: {t}'.format(t=temp_grade_showme_ded))

        try:
            temp_grade_hints_count = self.q_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_hints_count: {t}'.format(t=temp_grade_hints_count))

        try:
            temp_grade_hints_ded = self.q_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_hints_ded: {t}'.format(t=temp_grade_hints_ded))

        try:
            temp_grade_errors_count = self.q_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_errors_count: {t}'.format(t=temp_grade_errors_count))

        try:
            temp_grade_errors_ded = self.q_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_errors_ded: {t}'.format(t=temp_grade_errors_ded))

        try:
            temp_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_min_steps_count: {t}'.format(t=temp_grade_min_steps_count))

        try:
            temp_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_min_steps_ded: {t}'.format(t=temp_grade_min_steps_ded))

        try:
            temp_grade_app_key = self.q_grade_app_key
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_app_key was not defined in this instance: {e}'.format(e=e))
            temp_grade_app_key = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_app_key: {t}'.format(t=temp_grade_app_key))

        # Fetch the course-wide settings if they exist, otherwise create a default

        try:
            temp_course_stepwise_weight = course.stepwise_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_weight was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_weight = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_weight: {s}'.format(s=temp_course_stepwise_weight))

        try:
            temp_course_stepwise_max_attempts = course.stepwise_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_max_attempts = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_max_attempts: {s}'.format(s=temp_course_stepwise_max_attempts))

        try:
            temp_course_stepwise_option_showme = course.stepwise_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_option_showme was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_showme = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_option_showme: {s}'.format(s=temp_course_stepwise_option_showme))

        try:
            temp_course_stepwise_option_hint = course.stepwise_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_option_hint was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_hint = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_option_hint: {s}'.format(s=temp_course_stepwise_option_hint))

        try:
            temp_course_stepwise_grade_hints_count = course.stepwise_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_settings_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_hints_count: {s}'.format(s=temp_course_stepwise_grade_hints_count))

        try:
            temp_course_stepwise_grade_showme_ded = course.stepwise_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_showme_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_showme_ded: {s}'.format(s=temp_course_stepwise_grade_showme_ded))

        try:
            temp_course_stepwise_grade_hints_ded = course.stepwise_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_hints_ded: {s}'.format(s=temp_course_stepwise_grade_hints_ded))

        try:
            temp_course_stepwise_grade_errors_count = course.stepwise_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_errors_count: {s}'.format(s=temp_course_stepwise_grade_errors_count))

        try:
            temp_course_stepwise_grade_errors_ded = course.stepwise_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_errors_ded: {s}'.format(s=temp_course_stepwise_grade_errors_ded))

        try:
            temp_course_stepwise_grade_min_steps_count = course.stepwise_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_min_steps_count: {s}'.format(s=temp_course_stepwise_grade_min_steps_count))

        try:
            temp_course_stepwise_grade_min_steps_ded = course.stepwise_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_min_steps_ded: {s}'.format(s=temp_course_stepwise_grade_min_steps_ded))

        try:
            temp_course_stepwise_app_key = course.stepwise_grade_app_key
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_app_key was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_app_key = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_app_key: {s}'.format(s=temp_course_stepwise_grade_app_key))

        # Enforce course-wide grading options here.
        # We prefer the per-question setting to the course setting.
        # If neither the question setting nor the course setting exist, use the course default.

        if (temp_weight != -1):
            self.my_weight = temp_weight
        elif (temp_course_stepwise_weight != -1):
            self.my_weight = temp_course_stepwise_weight
        else:
            self.my_weight = def_course_stepwise_weight
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_weight={m}'.format(m=self.my_weight))

        # Set the real object weight here how that we know all of the weight settings (per-Q vs. per-course).
        # weight is used by the real grading code e.g. for overriding student scores.
        self.weight = self.my_weight
        if DEBUG: logger.info('SWPWRXBlock student_view() self.weight={m}'.format(m=self.weight))

        # For max_attempts: If there is a per-question max_attempts setting, use that.
        # Otherwise, if there is a course-wide stepwise_max_attempts setting, use that.
        # Otherwise, use the course-wide max_attempts setting that is used for CAPA (non-StepWise) problems.

        if temp_max_attempts is None:
            temp_max_attempts = -1

        if (temp_max_attempts != -1):
            self.my_max_attempts = temp_max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} temp_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_max_attempts))
        elif (temp_course_stepwise_max_attempts != -1):
            self.my_max_attempts = temp_course_stepwise_max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} temp_course_stepwise_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_course_stepwise_max_attempts))
        else:
            self.my_max_attempts = course.max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} course.max_attempts={m}'.format(a=self.my_max_attempts,m=course.max_attempts))

        if (temp_option_hint != -1):
            self.my_option_hint = temp_option_hint
        elif (temp_course_stepwise_option_hint != -1):
            self.my_option_hint = temp_course_stepwise_option_hint
        else:
            self.my_option_hint = def_course_stepwise_option_hint
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_option_hint={m}'.format(m=self.my_option_hint))

        if (temp_option_showme != -1):
            self.my_option_showme = temp_option_showme
        elif (temp_course_stepwise_option_showme != -1):
            self.my_option_showme = temp_course_stepwise_option_showme
        else:
            self.my_option_showme = def_course_stepwise_option_showme
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_option_showme={m}'.format(m=self.my_option_showme))

        if (temp_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_grade_showme_ded
        elif (temp_course_stepwise_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_course_stepwise_grade_showme_ded
        else:
            self.my_grade_showme_ded = def_course_stepwise_grade_showme_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_showme_ded={m}'.format(m=self.my_grade_showme_ded))

        if (temp_grade_hints_count != -1):
            self.my_grade_hints_count = temp_grade_hints_count
        elif (temp_course_stepwise_grade_hints_count != -1):
            self.my_grade_hints_count = temp_course_stepwise_grade_hints_count
        else:
            self.my_grade_hints_count = def_course_stepwise_grade_hints_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_hints_count={m}'.format(m=self.my_grade_hints_count))

        if (temp_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_grade_hints_ded
        elif (temp_course_stepwise_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_course_stepwise_grade_hints_ded
        else:
            self.my_grade_hints_ded = def_course_stepwise_grade_hints_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_hints_ded={m}'.format(m=self.my_grade_hints_ded))

        if (temp_grade_errors_count != -1):
            self.my_grade_errors_count = temp_grade_errors_count
        elif (temp_course_stepwise_grade_errors_count != -1):
            self.my_grade_errors_count = temp_course_stepwise_grade_errors_count
        else:
            self.my_grade_errors_count = def_course_stepwise_grade_errors_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_errors_count={m}'.format(m=self.my_grade_errors_count))

        if (temp_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_grade_errors_ded
        elif (temp_course_stepwise_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_course_stepwise_grade_errors_ded
        else:
            self.my_grade_errors_ded = def_course_stepwise_grade_errors_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_errors_ded={m}'.format(m=self.my_grade_errors_ded))

        if (temp_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_grade_min_steps_count
        elif (temp_course_stepwise_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_course_stepwise_grade_min_steps_count
        else:
            self.my_grade_min_steps_count = def_course_stepwise_grade_min_steps_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_min_steps_count={m}'.format(m=self.my_grade_min_steps_count))

        if (temp_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_grade_min_steps_ded
        elif (temp_course_stepwise_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_course_stepwise_grade_min_steps_ded
        else:
            self.my_grade_min_steps_ded = def_course_stepwise_grade_min_steps_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_min_steps_ded={m}'.format(m=self.my_grade_min_steps_ded))

        if (temp_grade_app_key != ""):
            self.my_grade_app_key = temp_grade_app_key
        elif (temp_course_stepwise_grade_app_key != ""):
            self.my_grade_app_key = temp_course_stepwise_grade_app_key
        else:
            self.my_grade_app_key = def_course_stepwise_grade_app_key

        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_app_key={m}'.format(m=self.my_grade_app_key))

        # Fetch the new xblock-specific attributes if they exist, otherwise set them to a default
        try:
            temp_value = self.q_swpwr_invalid_schemas
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_invalid_schemas was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_invalid_schemas = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_invalid_schemas: {t}'.format(t=self.q_swpwr_invalid_schemas))
        try:
            temp_value = self.q_swpwr_rank
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_rank was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_rank = DEFAULT_RANK
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_rank: {t}'.format(t=self.q_swpwr_rank))
        try:
            temp_value = self.q_swpwr_problem_hints
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_problem_hints was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_problem_hints = "[]"
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_problem_hints: {t}'.format(t=self.q_swpwr_problem_hints))

        # Save an identifier for the user

        user_service = self.runtime.service( self, 'user')
        xb_user = user_service.get_current_user()
        if DEBUG: logger.info('SWPWRXBlock student_view() xbuser: {e}'.format(e=xb_user))
        self.xb_user_email = xb_user.emails[0]
        if DEBUG: logger.info('SWPWRXBlock student_view() xb_user_email: {e}'.format(e=self.xb_user_email))

        # Determine which stepwise variant to use

        self.variants_count = 1

        if DEBUG: logger.info("SWPWRXBlock student_view() self.variants_count={c}".format(c=self.variants_count))
        # Pick a variant at random, and make sure that it is one we haven't attempted before.

        random.seed()                           # Use the clock to seed the random number generator for picking variants
        self.question = self.pick_variant()

        # question = self.question              # Don't need local var
        q_index = self.question['q_index']

        if DEBUG: logger.info("SWPWRXBlock student_view() pick_variant selected q_index={i} question={q}".format(i=q_index,q=self.question))

        html = self.resource_string("static/html/swpwrx2student.html")
        frag = Fragment(html.format(self=self))
        frag.add_resource('<meta charset="UTF-8"/>','text/html','head')
        frag.add_resource('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />','text/html','head')
        frag.add_resource('<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />','text/html','head')
        frag.add_resource('<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />','text/html','head')
        frag.add_resource('<link rel="manifest" href="/site.webmanifest" />','text/html','head')
        frag.add_resource('<meta name="viewport" content="width=device-width,initial-scale=1.0"/>','text/html','head')
        frag.add_resource('<link rel="preconnect" href="https://fonts.googleapis.com" />','text/html','head')
        frag.add_resource('<link rel="preconnect" href="https://fonts.googleapis.com" />','text/html','head')
        frag.add_resource('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />','text/html','head')
        frag.add_resource('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Irish+Grover&family=Sura:wght@400;700&display=swap" rel="stylesheet" />','text/html','head')
        frag.add_resource('<title>Querium StepWise Power</title>','text/html','head')
        frag.add_css(self.resource_string("static/css/swpwrx2student.css"))
        frag.add_javascript(self.resource_string("static/js/src/swpwrx2student.js"))

        # Add i18n js
        statici18n_js_url = self._get_statici18n_js_url()
        if statici18n_js_url:
            frag.add_javascript_url(self.runtime.local_resource_url(self, statici18n_js_url))

        # We no longer need to call final_callback.js since the code is generated in swpwr_string
        # frag.add_javascript(self.resource_string("static/js/src/final_callback.js"))
        invalid_schemas_js = self.q_swpwr_invalid_schemas
        if DEBUG: logger.info("SWPWRXBlock student_view() before mapping loop invalid_schemas_js={e}".format(e=invalid_schemas_js))
        mapping = { "TOTAL":"additiveTotalSchema", "DIFFERENCE":"additiveDifferenceSchema", "CHANGEINCREASE":"additiveChangeSchema", "CHANGEDECREASE":"subtractiveChangeSchema", "EQUALGROUPS":"multiplicativeEqualGroupsSchema", "COMPARE":"multiplicativeCompareSchema" }
        for schema_key, schema_value in mapping.items():
            invalid_schemas_js = invalid_schemas_js.replace(schema_key, schema_value)
            if DEBUG: logger.info("SWPWRXBlock student_view() in mapping loop schema_key={k} schema_value={v} invalid_schemas_js={e}".format(k=schema_key,v=schema_value,e=invalid_schemas_js))
        swpwr_string = 'window.swpwr = {' + \
                       '    options: {' + \
                       '        swapiUrl: "https://swapi2.onrender.com", ' + \
                       '        gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/", ' + \
                       '        rank: "' + self.q_swpwr_rank + '", ' + \
                       '        disabledSchemas: "' + invalid_schemas_js + '"' + \
                       '    }, ' + \
                       '    student: { ' + \
                       '        studentId: "' + self.xb_user_email + '", ' + \
                       '        fullName: "' + 'SAMPLE SAMPLE' + '", ' + \
                       '        familiarName: "' + 'SAMPLE' + '"' + \
                       '    },' + \
                       '    problem: { ' + \
                       '        appKey: "' + self.q_grade_app_key + '", ' + \
                       '        policyId: "' + '$A9$' + '", ' + \
                       '        problemId: "' + self.q_id + '", ' + \
                       '        title: "' + 'SAMPLE' + '", ' + \
                       '        stimulus: \'' + str(self.q_stimulus).replace('\'', '&apos;') + '\', ' + \
                       '        topic: "' + 'gradeBasicAlgebra' + '", ' + \
                       '        definition: \'' + str(self.q_definition).replace('\'', '&apos;') + '\', ' + \
                       '        wpHintsString: \'' + str(self.q_swpwr_problem_hints).replace('\'', '&apos;') + '\', ' + \
                       '        mathHints: [' + \
                       '                   "' + str(self.q_hint1).replace('\'', '&apos;').replace('\"', '&quot;') + '",' + \
                       '                   "' + str(self.q_hint2).replace('\'', '&apos;').replace('\"', '&quot;') + '",' + \
                       '                   "' + str(self.q_hint3).replace('\'', '&apos;').replace('\"', '&quot;') + '"' + \
                       '                   ]' + \
                       '    },' + \
                       '    handlers: {' + \
                       '        onComplete: (session,log) => {' + \
                       '            console.info("onComplete session",session);' + \
                       '            console.info("onComplete log",log);' + \
                       '            console.info("onComplete handlerUrlSwpwrResults",handlerUrlSwpwrResults);' + \
                       '            const solution = [session,log];' + \
                       '            var solution_string = JSON.stringify(solution);' + \
                       '            console.info("onComplete solution_string",solution_string);' + \
                       '            $.ajax({' + \
                       '                type: "POST",' + \
                       '                url: handlerUrlSwpwrResults,' + \
                       '                data: solution_string,' + \
                       '                success: function (data,msg) {' + \
                       '                    console.info("onComplete solution POST success");' + \
                       '                    console.info("onComplete solution POST data",data);' + \
                       '                    console.info("onComplete solution POST msg",msg);' + \
                       '                },' + \
                       '                error: function(XMLHttpRequest, textStatus, errorThrown) {' + \
                       '                    console.info("onComplete solution POST error textStatus=",textStatus," errorThrown=",errorThrown);' + \
                       '                }' + \
                       '            });' + \
                       '            $(\'.problem-complete\').show();' + \
                       '            $(\'.unit-navigation\').show();' + \
                       '        }' + \
                       '    }' + \
                       '};' + \
                       'try { ' + \
                       '    console.log( "before JSON.parse wpHintsString ",window.swpwr.problem.wpHintsString);' + \
                       '    window.swpwr.problem.wpHints = JSON.parse(window.swpwr.problem.wpHintsString);' + \
                       '    console.log( "wpHints data is ",window.swpwr.problem.wpHints );' + \
                       '} catch(e) {' + \
                       '    console.log( "Could not decode wpHints string",e.message );' + \
                       '};'
        if DEBUG: logger.info("SWPWRXBlock student_view() swpwr_string={e}".format(e=swpwr_string))
        frag.add_resource(swpwr_string,'application/javascript','foot')

        frag.initialize_js('Swpwrx2student', {})   # Call the entry point
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

        # if DEBUG: logger.info("Swpwrx2 author_view v={a}".format(a=self.q_definition))

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

    # SAVE QUESTION
    @XBlock.json_handler
    def save_question(self, data, suffix=''):
        if DEBUG: logger.info('SWPWRXBlock save_question() entered')
        if DEBUG: logger.info('SWPWRXBlock save_question() data={d}'.format(d=data))
        try:
            self.q_max_attempts = int(data['q_max_attempts'])
        except:
            if DEBUG: logger.info("SWPWRXBlock save_question() could not fetch data[q_max_attempts]. Assuming 1000.")
            self.q_max_attempts = 1000;
        self.q_weight = float(data['q_weight'])
        if data['q_option_showme'].lower() == u'true':
            self.q_option_showme = True
        else:
            self.q_option_showme = False
        if data['q_option_hint'].lower() == u'true':
            self.q_option_hint = True
        else:
            self.q_option_hint = False
        self.q_grade_showme_ded = float(data['q_grade_showme_ded'])
        self.q_grade_hints_count = int(data['q_grade_hints_count'])
        self.q_grade_hints_ded = float(data['q_grade_hints_ded'])
        self.q_grade_errors_count = int(data['q_grade_errors_count'])
        self.q_grade_errors_ded = float(data['q_grade_errors_ded'])
        self.q_grade_min_steps_count = int(data['q_grade_min_steps_count'])
        self.q_grade_min_steps_ded = float(data['q_grade_min_steps_ded'])
        self.q_grade_app_key = str(data['q_grade_app_key'])

        self.q_id = data['id']
        self.q_label = data['label']
        self.q_stimulus = data['stimulus']
        self.q_definition = data['definition']
        self.q_type = data['qtype']
        self.q_display_math = data['display_math']
        self.q_hint1 = data['hint1']
        self.q_hint2 = data['hint2']
        self.q_hint3 = data['hint3']
        self.q_swpwr_problem = data['swpwr_problem']
        self.q_swpwr_rank = data['swpwr_rank']
        self.q_swpwr_invalid_schemas = data['swpwr_invalid_schemas']
        self.q_swpwr_problem_hints = data['swpwr_problem_hints']

        self.display_name = "Step-by-Step POWER"

        # mcdaniel jul-2020: fix syntax error in print statement
        print(self.display_name)
        return {'result': 'success'}


# SWPWR RESULTS: Save the final results of the SWPWR React app as a stringified structure.
    @XBlock.json_handler
    def save_swpwr_results(self, data, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_results() data={d}".format(d=data))
        self.swpwr_results = json.dumps(data, separators=(',', ':'))
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_results() self.swpwr_results={r}".format(r=self.swpwr_results))
        self.save() # Time to persist our state!!!
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_results() back from save")
        return {'result': 'success'}

    # Do necessary overrides from ScorableXBlockMixin
    def has_submitted_answer(self):
        if DEBUG: logger.info('SWPWRXBlock has_submitted_answer() entered')
        """
        Returns True if the problem has been answered by the runtime user.
        """
        if DEBUG: logger.info("SWPWRXBlock has_submitted_answer() {a}".format(a=self.is_answered))
        return self.is_answered


    def get_score(self):
        if DEBUG: logger.info('SWPWRXBlock get_score() entered')
        """
        Return a raw score already persisted on the XBlock.  Should not
        perform new calculations.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWPWRXBlock get_score() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWPWRXBlock get_score() max {m}".format(m=self.max_score()))
        return Score(float(self.raw_earned), float(self.max_score()))


    def set_score(self, score):
        """
        Persist a score to the XBlock.
        The score is a named tuple with a raw_earned attribute and a
        raw_possible attribute, reflecting the raw earned score and the maximum
        raw score the student could have earned respectively.
        Arguments:
            score: Score(raw_earned=float, raw_possible=float)
        Returns:
            None
        """
        if DEBUG: logger.info("SWPWRXBlock set_score() earned {e}".format(e=score.raw_earned))
        self.raw_earned = score.raw_earned


    def calculate_score(self):
        """
        Calculate a new raw score based on the state of the problem.
        This method should not modify the state of the XBlock.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWPWRXBlock calculate_score() grade {g}".format(g=self.grade))
        if DEBUG: logger.info("SWPWRXBlock calculate_score() max {m}".format(m=self.max_score))
        return Score(float(self.grade), float(self.max_score()))


    def allows_rescore(self):
        """
        Boolean value: Can this problem be rescored?
        Subtypes may wish to override this if they need conditional support for
        rescoring.
        """
        if DEBUG: logger.info("SWPWRXBlock allows_rescore() False")
        return False


    def max_score(self):
        """
        Function which returns the max score for an xBlock which emits a score
        https://openedx.atlassian.net/wiki/spaces/AC/pages/161400730/Open+edX+Runtime+XBlock+API#OpenedXRuntimeXBlockAPI-max_score(self):
        :return: Max Score for this problem
        """
        # Want the normalized, unweighted score here (1), not the points possible (3)
        return 1


    def weighted_grade(self):
        """
        Returns the block's current saved grade multiplied by the block's
        weight- the number of points earned by the learner.
        """
        if DEBUG: logger.info("SWPWRXBlock weighted_grade() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWPWRXBlock weighted_grade() weight {w}".format(w=self.q_weight))
        return self.raw_earned * self.q_weight


    def bit_count_ones(self,var):
        """
        Returns the count of one bits in an integer variable
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_count_ones var={v}".format(v=var))
        count=0
        bits = var
        for b in range(32):
            lsb = (bits >> b) & 1;
            count = count + lsb;
        if DEBUG: logger.info("SWPWRXBlock bit_count_ones result={c}".format(c=count))
        return count


    def bit_set_one(self,var,bitnum):
        """
        return var = var with bit 'bitnum' set
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_set_one var={v} bitnum={b}".format(v=var,b=bitnum))
        var = var | (1 << bitnum)
        if DEBUG: logger.info("SWPWRXBlock bit_set_one result={v}".format(v=var))
        return var


    def bit_is_set(self,var,bitnum):
        """
        return True if bit bitnum is set in var
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_is_set var={v} bitnum={b}".format(v=var,b=bitnum))
        result = var & (1 << bitnum)
        if DEBUG: logger.info("SWPWRXBlock bit_is_set result={v} b={b}".format(v=result,b=bool(result)))
        return bool(result)


    def pick_variant(self):
       # pick_variant() selects one of the available question variants that we have not yet attempted.
       # If there is only one variant left, we have to return that one.
       # If there are 2+ variants left, do not return the same one we started with.
       # If we've attempted all variants, we clear the list of attempted variants and pick again.
       #  Returns the question structure for the one we will use this time.

        try:
            prev_index = self.q_index
        except (NameError,AttributeError) as e:
            prev_index = -1

        if DEBUG: logger.info("SWPWRXBlock pick_variant() started replacing prev_index={p}".format(p=prev_index))

        # If there's no self.q_index, then this is our first look at this question in this session, so
        # use self.previous_variant if we can.  This won't restore all previous attempts, but makes sure we
        # don't use the variant that is displayed in the student's last attempt data.
        if (prev_index == -1):
            try:         # use try block in case attribute wasn't saved in previous student work
                 prev_index = self.previous_variant
                 if DEBUG: logger.info("SWPWRXBlock pick_variant() using previous_variant for prev_index={p}".format(p=prev_index))
            except (NameError,AttributeError) as e:
                 if DEBUG: logger.info("SWPWRXBlock pick_variant() self.previous_variant does not exist. Using -1: {e}".format(e=e))
                 prev_index = -1

        if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
            if DEBUG: logger.warn("SWPWRXBlock pick_variant() seen all variants attempted={a} count={c}, clearing variants_attempted".format(a=self.variants_attempted,c=self.variants_count))
            self.variants_attempted = 0			# We have not yet attempted any variants

        tries = 0					# Make sure we dont try forever to find a new variant
        max_tries = 100

        if self.variants_count <= 0:
            if DEBUG: logger.warn("SWPWRXBlock pick_variant() bad variants_count={c}, setting to 1.".format(c=self.variants_count))
            self.variants_count = 1;

        while tries<max_tries:
            tries=tries+1
            q_randint = random.randint(0, ((self.variants_count*100)-1))	# 0..999 for 10 variants, 0..99 for 1 variant, etc.
            if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: q_randint={r}".format(t=tries,r=q_randint))

            if q_randint>=0 and q_randint<100:
                q_index=0
            elif q_randint>=100 and q_randint<200:
                q_index=1
            elif q_randint>=200 and q_randint<300:
                q_index=2
            elif q_randint>=300 and q_randint<400:
                q_index=3
            elif q_randint>=400 and q_randint<500:
                q_index=4
            elif q_randint>=500 and q_randint<600:
                q_index=5
            elif q_randint>=600 and q_randint<700:
                q_index=6
            elif q_randint>=700 and q_randint<800:
                q_index=7
            elif q_randint>=800 and q_randint<900:
                q_index=8
            else:
                q_index=9

            # If there are 2+ variants left and we have more tries left, do not return the same variant we started with.
            if q_index == prev_index and tries<max_tries and self.bit_count_ones(self.variants_attempted) < self.variants_count-1:
                if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: with bit_count_ones(variants_attempted)={v} < variants_count={c}-1 we won't use the same variant {q} as prev variant".format(t=tries,v=self.bit_count_ones(self.variants_attempted),c=self.variants_count,q=q_index))
                break

            if not self.bit_is_set(self.variants_attempted,q_index):
                if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: found unattempted variant {q}".format(t=tries,q=q_index))
                break
            else:
                if DEBUG: logger.info("pick_variant() try {t}: variant {q} has already been attempted".format(t=tries,q=q_index))
                if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
                    if DEBUG: logger.info("pick_variant() try {t}: we have attempted all {c} variants. clearning self.variants_attempted.".format(t=tries,c=self.bit_count_ones(self.variants_attempted)))
                    q_index = 0		# Default
                    self.variants_attempted = 0;
                    break

        if tries>=max_tries:
            if DEBUG: logger.error("pick_variant() could not find an unattempted variant of {l} in {m} tries! clearing self.variants_attempted.".format(l=self.q_label,m=max_tries))
            q_index = 0		# Default
            self.variants_attempted = 0;

        if DEBUG: logger.info("pick_variant() Selected variant {v}".format(v=q_index))

        # Note: we won't set self.variants_attempted for this variant until they actually begin work on it (see start_attempt() below)

        question = {
            "q_id" : self.q_id,
            "q_user" : self.xb_user_email,
            "q_index" : 0,
            "q_label" : self.q_label,
            "q_stimulus" : self.q_stimulus,
            "q_definition" : self.q_definition,
            "q_type" :  self.q_type,
            "q_display_math" :  self.q_display_math,
            "q_hint1" :  self.q_hint1,
            "q_hint2" :  self.q_hint2,
            "q_hint3" :  self.q_hint3,
            "q_swpwr_problem" : self.q_swpwr_problem,
            "q_swpwr_rank": self.q_swpwr_rank,
            "q_swpwr_invalid_schemas": self.q_swpwr_invalid_schemas,
            "q_swpwr_problem_hints": self.q_swpwr_problem_hints,
            "q_weight" :  self.my_weight,
            "q_max_attempts" : self.my_max_attempts,
            "q_option_hint" : self.my_option_hint,
            "q_option_showme" : self.my_option_showme,
            "q_grade_showme_ded" : self.my_grade_showme_ded,
            "q_grade_hints_count" : self.my_grade_hints_count,
            "q_grade_hints_ded" : self.my_grade_hints_ded,
            "q_grade_errors_count" : self.my_grade_errors_count,
            "q_grade_errors_ded" : self.my_grade_errors_ded,
            "q_grade_min_steps_count" : self.my_grade_min_steps_count,
            "q_grade_min_steps_ded" : self.my_grade_min_steps_ded,
            "q_grade_app_key" : self.my_grade_app_key
        }

        if DEBUG: logger.info("SWPWRXBlock pick_variant() returned question q_index={i} question={q}".format(i=question['q_index'],q=question))
        return question
