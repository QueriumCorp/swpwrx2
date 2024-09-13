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
from xblockutils.resources import ResourceLoader
from xblock.scorable import ScorableXBlockMixin, Score
from xblockutils.studio_editable import StudioEditableXBlockMixin
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
    my_grade_app_key  = String(help="SWPWR Remember app_key course setting vs question setting", default=-1, scope=Scope.user_state)

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

        if DEBUG: logger.info("SWPWRXBlock student_view() max_attempts={a} q_max_attempts={b}".format(a=self.max_attempts,b=self.q_max_attempts))

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

        frag.add_javascript(self.resource_string("static/js/src/final_callback.js"))    # Final submit callback code and define swpwr_problems[]
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
