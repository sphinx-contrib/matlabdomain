"""sphinxcontrib.mat_documenters.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend autodoc directives to matlabdomain.

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import difflib
import json
import re
from typing import Any, cast

from sphinx.ext.autodoc import (
    ALL,
    EMPTY,
    SUPPRESS,
    annotation_option,
    bool_option,
    exclude_members_option,
    identity,
    members_option,
)
from sphinx.ext.autodoc import (
    DataDocumenter as PyDataDocumenter,
)
from sphinx.ext.autodoc import (
    Documenter as PyDocumenter,
)
from sphinx.ext.autodoc import (
    ModuleDocumenter as PyModuleDocumenter,
)
from sphinx.locale import _
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import safe_getattr
from sphinx.util.logging import getLogger

from . import mat_naming, mat_sidecars, mat_simulink
from .mat_classify import is_hidden
from .mat_types import (
    SIMULINK_CLASSES,
    MatApplication,
    MatBlock,
    MatClass,
    MatcodeError,
    MatEnumeration,
    MatEvent,
    MatFunction,
    MatLibrary,
    MatMethod,
    MatModule,
    MatModuleAnalyzer,
    MatProperty,
    MatScript,
    MatSimulinkFile,
    display_name,
    find_source,
    is_code_object,
    is_folder_object,
    is_source_object,
    lookup_reference,
    resolve,
    same_block,
    simulink_accepts,
    warn_ambiguous,
)

mat_ext_sig_re = re.compile(
    r"""^ ([+@]?[+@\w.]+::)?            # explicit module name
          ([+@]?[+@\w.]+\.)?            # module and/or class name(s)
          ([+@]?\w+)  \s*               # thing name
          (?: \((.*)\)                  # optional: arguments
           (?:\s* -> \s* (.*))?         #           return annotation
          )? $                          # and nothing more
          """,
    re.VERBOSE,
)

# Auto directive argument: a path reference or MATLAB name, then an optional
# signature.
mat_auto_sig_re = re.compile(
    r"""^ (.+?) \s*                     # path reference or MATLAB name
          (?: \(([^()]*)\)              # optional: arguments
           (?:\s* -> \s* (.*))?         #           return annotation
          )? $                          # and nothing more
          """,
    re.VERBOSE,
)


# TODO: check MRO's for all classes, attributes and methods!!!

#: options of the documenters with members (classes and folders)
MEMBER_OPTIONS = {
    "members": members_option,
    "undoc-members": bool_option,
    "noindex": bool_option,
    "no-index": bool_option,
    "show-inheritance": bool_option,
    "member-order": identity,
    "exclude-members": exclude_members_option,
    "private-members": members_option,
    "protected-members": members_option,
    "hidden-members": members_option,
    "access-list-members": members_option,
    # the old name of access-list-members
    "friend-members": members_option,
}


logger = getLogger("matlab-domain")

# Inline markup must follow whitespace or one of these characters, and precede
# whitespace or one of the others (docutils); elsewhere an escaped space,
# which the output drops, separates a link from the text around it.
_MARKUP_BEFORE = frozenset("-:/'\"<([{")
_MARKUP_AFTER = frozenset("-.,:;!?\\/'\")]}>")
#: roles of files that "See also" and auto-links name (``ref_role``)
_FILE_ROLES = (
    "class",
    "func",
    "simulink_model",
    "simulink_library",
    "simulink_subsystem_reference",
)


def _inline(match, markup):
    """Return ``markup`` to replace ``match``, valid next to the text around it."""
    text, start, end = match.string, match.start(), match.end()
    if start and not (text[start - 1].isspace() or text[start - 1] in _MARKUP_BEFORE):
        markup = "\\ " + markup
    if end < len(text) and not (text[end].isspace() or text[end] in _MARKUP_AFTER):
        markup += "\\ "
    return markup


def follow_lines(before, numbers, after, start):
    """Return the line numbers of the lines ``after``, a changed copy of the
    lines ``before`` numbered ``numbers``: a kept line keeps its number, a line
    of a changed block has the number of the block's first line (or of its
    own line if the block keeps its size), an added line that of the line
    before it (``start`` at the beginning).
    """
    found, last = [], start
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            found += numbers[i1:i2]
        elif tag == "replace":
            found += [numbers[i1]] * (j2 - j1)
        elif tag == "insert":
            found += [last] * (j2 - j1)
        last = found[-1] if found else start
    return found


class MatlabDocumenter(PyDocumenter):
    """Base class for documenters of MATLAB objects."""

    domain = "mat"
    #: True for members of a class (methods, attributes)
    class_level = False
    #: splits the auto directive's argument into (target, arguments, return)
    name_pattern = mat_auto_sig_re
    option_spec = {"noindex": bool_option, "no-index": bool_option}
    analyzer: MatModuleAnalyzer | None
    options: Any

    def parse_name(self):
        """Resolve *self.name* to the object to document (plan.md Section 2.3).

        Sets *self.ref* (path reference), *self.display* (MATLAB name),
        *self.modname* (folder reference), *self.objpath* (file stem and
        members), *self.fullname* (the reference), *self.args* and
        *self.retann*. Returns False (after a warning) if *self.name* does
        not name exactly one object.
        """
        match = self.name_pattern.match(self.name)
        if match is None:  # pragma: no cover - the re matches any non-empty name
            logger.warning(
                "[sphinxcontrib-matlabdomain] Invalid signature for mat:auto%s (%r)",
                self.objtype,
                self.name,
                type="mat",
                subtype="directive",
            )
            return False
        target, args, retann = match.groups()

        dom = self.env.get_domain("mat")
        found = []
        cls = self.env.temp_data.get("mat:class")
        if self.class_level and cls:
            obj = lookup_reference(dom, f"{cls[0]}.{target}")
            if obj is not None and self.accepts(obj):
                found = [(f"{cls[0]}.{target}", obj)]
        if not found:
            found = find_source(
                dom, target, self.env.temp_data.get("mat:folder"), self.accepts
            )
        if len(found) != 1:
            location = (self.env.docname, self.directive.lineno)
            if found:
                warn_ambiguous(target, [ref for ref, _ in found], location)
            else:
                logger.warning(
                    "[sphinxcontrib-matlabdomain] don't know which object to "
                    "document for %r (use a path reference, a MATLAB name, or a "
                    '"mat:currentfolder" directive)',
                    self.name,
                    type="mat",
                    subtype="not_found",
                    location=location,
                )
                self.env.note_reread()
            return False

        self.ref, self._resolved = found[0]
        self.display = display_name(dom, self.ref)
        file, members = mat_naming.parse_reference(self.ref)
        if isinstance(self._resolved, MatModule):
            self.modname, self.objpath = self.ref, []
        else:
            file = cast(str, file)
            stem = file.rpartition("/")[2].rpartition(".")[0]
            self.modname = mat_naming.folder_of(file)
            self.objpath = [stem, *members]
        self.args = args
        self.retann = retann
        self.fullname = self.ref
        return True

    def import_object(self):
        """Set the object resolved by :meth:`parse_name` as *self.object*."""
        self.object = self._resolved
        return True

    def get_doc(self) -> list[list[str]]:
        return super().get_doc() or []

    #: True for the objects this documenter documents (folders or not)
    accepts = staticmethod(is_code_object)

    def format_name(self):
        return self.display

    def add_directive_header(self, sig):
        """Add the directive header and options to the generated content."""
        directive = getattr(self, "directivetype", self.objtype)
        sourcename = self.get_sourcename()

        self.add_line(
            f".. {self.domain}:{directive}:: {self.format_name()}{sig}", sourcename
        )

        if self.options.no_index or self.options.noindex:
            self.add_line("   :noindex:", sourcename)
        self.add_line(f"   :reference: {self.ref}", sourcename)

    def add_flags(self, attrs, flags):
        """Add the flag options (``:abstract:``) whose MATLAB attribute is set."""
        for flag, attr in flags:
            if attrs.get(attr):
                self.add_line(f"   :{flag}:", self.get_sourcename())

    def add_content(self, more_content, no_docstring=False):
        """Add content from docstrings, attribute documentation and user."""
        sourcename = self.help_source()

        # add content from docstrings (autodoc API: this extension never
        # passes no_docstring)
        if not no_docstring:  # pragma: no branch
            docstrings = self.get_doc()
            if not docstrings:
                # append at least a dummy docstring, so that the event
                # autodoc-process-docstring is fired and can add some
                # content if desired
                docstrings.append([])
            numbers = self.help_line_numbers(docstrings)
            if self.env.config.matlab_auto_link:
                docstrings = self.auto_link(docstrings)
            for docstring, lines in zip(docstrings, numbers, strict=True):
                before = list(docstring)
                # ``autodoc-process-docstring`` handlers (napoleon) may change it
                processed = list(self.process_doc([docstring]))
                start = lines[0] if lines else self.help_start()
                after = follow_lines(before, lines, processed, start)
                for line, number in zip(processed, after, strict=True):
                    # ``add_line`` takes a zero-based offset; docutils adds one.
                    self.add_line(line, sourcename, number - 1)

        # add additional content (e.g. from document), if present
        if more_content:
            for line, src in zip(more_content.data, more_content.items, strict=False):
                self.add_line(line, src[0], src[1])

    def help_source(self):
        """Source of the help lines: ``<file>:docstring of <reference>``, as
        Python's autodoc names it (the file only without an index).
        """
        file = mat_naming.parse_reference(self.ref)[0]
        path = cast(Any, self.env.get_domain("mat")).source_paths().get(file)
        return mat_sidecars.help_source(self.fullname, path)

    def help_sources(self):
        """``(help, line)`` of each help text of the object, in order: the help
        and the one-based file line it starts on (None: there are no file
        lines, as in a Simulink file, so the lines of the help count).
        """
        obj = self.object
        return [(getattr(obj, "docstring", None), getattr(obj, "docstring_line", None))]

    def help_start(self):
        """One-based line the help of the object starts on, or 1."""
        obj = self.object
        return getattr(obj, "docstring_line", None) or getattr(obj, "line", None) or 1

    def help_line_numbers(self, docstrings):
        """For each line of ``docstrings`` (prepared help), its one-based line
        in the file, found by comparing the words of the lines with the
        object's help (``help_sources``; see ``follow_lines``).
        """
        raw = [
            ((first or 1) + i, " ".join(line.split()))
            for text, first in self.help_sources()
            for i, line in enumerate((text or "").split("\n"))
        ]
        words, lines = [w for _, w in raw], [n for n, _ in raw]
        start = lines[0] if lines else self.help_start()
        return [
            follow_lines(words, lines, [" ".join(x.split()) for x in doc], start)
            for doc in docstrings
        ]

    def class_object(self) -> MatClass | None:
        # the associated MatClass object (for class, property and method documenters)
        return None

    def auto_link_basic(self, docstrings):
        return self.auto_link_see_also(docstrings)

    def _link(self, role, text, ref):
        # The title is explicit, so add the parentheses an implicit one gets.
        if role in ("func", "meth"):
            text = text.removesuffix("()")
            if self.env.config.add_function_parentheses:
                text += "()"
        return f":mat:{role}:`{text} <{ref}>`"

    def _find_link(self, target):
        """Return the (reference, object) ``target`` names from this object's folder.

        A MATLAB name of several objects warns and returns None; with
        ``matlab_link_shadowed_files_to_chooser_pages`` it returns ``(target, None)``, a
        reference to the name (its chooser page).
        """
        found = find_source(
            self.env.get_domain("mat"),
            target,
            mat_naming.folder_of(self.ref),
            is_source_object,
        )
        if len(found) > 1:
            if self.env.config.matlab_link_shadowed_files_to_chooser_pages:
                return target, None
            logger.warning(
                "[sphinxcontrib-matlabdomain] %r in the docstring of %s matches "
                "several objects: %s; use a path reference",
                target,
                self.ref,
                ", ".join(sorted(ref for ref, _ in found)),
                type="mat",
                subtype="ambiguous",
            )
            return None
        return found[0] if found else None

    def auto_link_see_also(self, docstrings):
        # autolink known names in See also
        see_also_re = re.compile(r"^(\s*See also:?\s*)(\b.*\b)(.*)", re.IGNORECASE)
        see_also_cond_re = re.compile(r"(\s*)(\b.*\b)(.*)")
        is_see_also_line = False
        for i in range(len(docstrings)):
            for j in range(len(docstrings[i])):
                if line := docstrings[i][j]:
                    if is_see_also_line:
                        # find name
                        match = see_also_cond_re.search(line)
                        if match is None:  # no names, e.g. a "---" line
                            is_see_also_line = False
                            continue
                        entries_str = match.group(2)  # the entries
                    elif match := see_also_re.search(line):
                        is_see_also_line = True  # line begins with "See also"
                        entries_str = match.group(2)  # the entries
                elif is_see_also_line:  # blank line following see also section
                    is_see_also_line = False  # end see also section

                if is_see_also_line and entries_str:
                    match = cast(re.Match[str], match)
                    tail = match.group(3)
                    # "See also f()": the parentheses are the last entry's
                    if tail.startswith("()"):
                        entries_str, tail = entries_str + "()", tail[2:]
                    # split on ,
                    entries = re.split(r"\s*,\s*", entries_str)
                    for k in range(len(entries)):
                        if entries[k].endswith("`"):
                            continue

                        # a class or function (path reference or MATLAB name)
                        found = self._find_link(entries[k].rstrip("()"))
                        if found is not None and found[1] is None:
                            entries[k] = self._link("obj", entries[k], found[0])
                            continue
                        role = found[1].ref_role() if found is not None else None
                        if found is not None and role in _FILE_ROLES:
                            entries[k] = self._link(role, entries[k], found[0])
                            continue

                        # if we have an associated class, search properties and methods
                        if cls := self.class_object():
                            name = entries[k].rstrip("()")
                            if name in cls.methods:
                                entries[k] = (
                                    f":mat:meth:`{name}() "
                                    f"<{cls.fullname(self.env)}.{name}>`"
                                )
                                continue
                            elif name in cls.properties:
                                entries[k] = (
                                    f":mat:attr:`{name} "
                                    f"<{cls.fullname(self.env)}.{name}>`"
                                )
                                continue
                            elif name in cls.events:
                                entries[k] = (
                                    f":mat:event:`{name} "
                                    f"<{cls.fullname(self.env)}.{name}>`"
                                )
                                continue

                        # a method, property or event of another class
                        if found is not None and role in ["meth", "attr", "event"]:
                            entries[k] = self._link(role, entries[k], found[0])
                            continue

                        # not yet handled
                        entries[k] = f"``{entries[k]}``"

                    if tail and not (tail[0].isspace() or tail[0] in _MARKUP_AFTER):
                        tail = "\\ " + tail
                    docstrings[i][j] = match.group(1) + ", ".join(entries) + tail
        return docstrings

    def detect_literal_block(self, line, no_link_state):
        # skip over literal blocks (i.e. line ending with ::, blank line, indented line)
        # returns not_in_literal_block = True if the line is not in a literal block
        not_in_literal_block = False
        if line.endswith("::"):
            no_link_state = -1  # 1st sign of literal block
        elif not line:  # blank line
            if no_link_state == -1:  # if 1st sign already detected
                no_link_state = -2  # 2nd sign of literal block
            elif no_link_state == 1:  # if in literal block
                no_link_state = -2  # need to look again for indented line
        elif no_link_state == -2:  # following 1st 2 signs
            if line.startswith("  "):  # indented line, literal block
                no_link_state = 1  # no linking!
            else:  # not indented line, literal block has ended
                no_link_state = 0  # restart linking!
                not_in_literal_block = True  # including in this line
        elif no_link_state != 1:  # not in a literal block, go ahead and link
            not_in_literal_block = True

        return not_in_literal_block, no_link_state

    def auto_link_all(self, docstrings):
        # auto-link known classes and functions everywhere
        dom = self.env.get_domain("mat")
        folder = mat_naming.folder_of(self.ref)
        # negative look-behind for ` . + < @ * / | <non-breaking space>
        look_behind = r"(?<!(`|\.|\+|<|@|\*| |/|\|))\b"
        # negative look-ahead for ` * / | or <non-breaking space> or
        # " Properties:" or " Methods:" or .<alphanum>
        look_ahead = r"\b(?!(`|\*| |\sProperties:|\sMethods:|\.\w|/|\|))"
        look_ahead2 = r"\b(?!(`|\*| |\sProperties:|\sMethods:|/|\|))"
        for nn in list(dom.data["matlab_names"]):
            # Only names in the text can link; resolving parses their files.
            if not any(nn in line for lines in docstrings for line in lines):
                continue
            found = find_source(dom, nn, folder, is_source_object)
            if not found:
                continue
            # entity_name is NOT followed by .<property_or_method>
            p = re.compile(look_behind + re.escape(nn) + look_ahead)
            if len(found) > 1:
                if not any(p.search(line) for lines in docstrings for line in lines):
                    continue
                # warns about the ambiguity, or gives the name to link
                if self._find_link(nn) is None:
                    continue
                ref, o, role = nn, None, "obj"
            else:
                ref, o = found[0]
                role = o.ref_role()
            if role in (*_FILE_ROLES, "obj"):
                if role == "class":
                    o = cast(MatClass, o)
                    # entity_name IS followed by .<property_or_method>
                    p2 = re.compile(
                        look_behind + re.escape(nn) + r"\.(\w+)" + look_ahead2
                    )
                no_link_state = 0  # normal mode (no literal block detected)
                for i in range(len(docstrings)):
                    for j in range(len(docstrings[i])):
                        not_in_literal_block, no_link_state = self.detect_literal_block(
                            docstrings[i][j], no_link_state
                        )
                        if not_in_literal_block:
                            link = self._link(role, nn, ref)
                            docstrings[i][j] = p.sub(
                                lambda m, t=link: _inline(m, t), docstrings[i][j]
                            )
                            if role == "class":
                                if match := p2.search(docstrings[i][j]):
                                    # if match.group(1) is a property
                                    #   -> :attr:`{nn}.{match.group(1)}`
                                    for nnn in cast(MatClass, o).properties:
                                        if match.group(2) == nnn:
                                            text = self._link(
                                                "attr", f"{nn}.{nnn}", f"{ref}.{nnn}"
                                            )
                                            docstrings[i][j] = p2.sub(
                                                lambda m, t=text: _inline(m, t),
                                                docstrings[i][j],
                                            )
                                            break
                                    # if match.group(1) is a method
                                    #   -> :meth:`{nn}.{match.group(1)}`
                                    for nnn in cast(MatClass, o).methods:
                                        if match.group(2) == nnn:
                                            text = self._link(
                                                "meth", f"{nn}.{nnn}", f"{ref}.{nnn}"
                                            )
                                            docstrings[i][j] = p2.sub(
                                                lambda m, t=text: _inline(m, t),
                                                docstrings[i][j],
                                            )
                                            break

        return docstrings

    def auto_link(self, docstrings):
        # called for "basic" or "all" (matlab_auto_link is set)
        docstrings = self.auto_link_basic(docstrings)

        # auto-link everywhere
        if self.env.config.matlab_auto_link == "all":
            docstrings = self.auto_link_all(docstrings)

        return docstrings

    def auto_link_methods(self, class_obj, docstrings):
        for n in class_obj.methods:
            # negative look-behind for ` . < @ * / | <non-breaking space>, then
            # <name>()
            pat = r"(?<!(`|\.|<|@|\*| |/|\|))\b" + n + r"\(\)(?! |\|)"
            p = re.compile(pat)
            no_link_state = 0  # normal mode (no literal block detected)
            for i in range(len(docstrings)):
                for j in range(len(docstrings[i])):
                    not_in_literal_block, no_link_state = self.detect_literal_block(
                        docstrings[i][j], no_link_state
                    )
                    if not_in_literal_block:
                        link = f":mat:meth:`{n}() <{class_obj.fullname(self.env)}.{n}>`"
                        docstrings[i][j] = p.sub(
                            lambda m, t=link: _inline(m, t), docstrings[i][j]
                        )

        return docstrings

    def get_object_members(self, want_all):
        """Return `(members_check_module, members)` where `members` is a
        list of `(membername, member)` pairs of the members of *self.object*.

        If *want_all* is True, return all members.  Else, only return those
        members given by *self.options.members* (which may also be none).
        """
        if not want_all:
            if not self.options.members:
                return False, []

            # specific members given
            members = []
            for mname in self.options.members:
                if (member := self.get_attr(self.object, mname, None)) is not None:
                    members.append((mname, member))
                else:
                    logger.warning(
                        (
                            "[sphinxcontrib-matlabdomain] "
                            "missing attribute %s in object %s"
                        ),
                        mname,
                        self.fullname,
                        type="mat",
                        subtype="not_found",
                    )
        else:
            # __dict__ contains only the members directly defined in
            # the class (but get them via getattr anyway, to e.g. get
            # unbound method objects instead of function objects);
            # using keys() because apparently there are objects for which
            # __dict__ changes while getting attributes
            try:
                obj_dict = self.get_attr(self.object, "__dict__")
            except AttributeError:  # pragma: no cover - defensive: classes have one
                members = []
            else:
                members = [
                    (mname, self.get_attr(self.object, mname, None))
                    for mname in list(obj_dict.keys())
                ]
        return False, sorted(members)

    def filter_members(self, members: list[tuple[str, Any]], want_all):
        """Filter the given member list.

        Members are skipped if

        - they are private (except if given explicitly or the private-members
          option is set)
        - they are protected (except if given explicitly or the protected-members
          option is set)
        - they are hidden (except if given explicitly or the hidden-members
          option is set)
        - their access is a list of classes (``Access = ?Cls`` or ``{?A, ?B}``;
          except if given explicitly or the access-list-members option, or its
          old name friend-members, is set)

        - they are undocumented (except if the undoc-members option is set)

        The user can override the skipping decision by connecting to the
        ``autodoc-skip-member`` event.
        """

        def access_of(member, name):
            # ``Access = 'private'`` is ``Access = private``
            value = (self.get_attr(member, "attrs", None) or {}).get(name)
            return value.strip("'\"") if isinstance(value, str) else value

        def access_list(value):
            # ``?Cls`` or ``{?A, ?B}`` (without ``?``), else None
            if isinstance(value, str):
                value = [value] if value.startswith("?") else None
            if not isinstance(value, list):
                return None
            return [name.lstrip("?") for name in value]

        # :friend-members: is the old name of :access-list-members:; class
        # names match with or without ``?``
        access_lists = self.options.access_list_members or self.options.friend_members
        if isinstance(access_lists, list):
            access_lists = [name.lstrip("?") for name in access_lists]

        ret = []

        # process members and determine which to skip
        for membername, member in members:
            # if isattr is True, the member is documented as an attribute
            isattr = False

            has_doc = bool(self.get_attr(member, "__doc__", None))
            # a library block with a section in the documentation file
            has_doc = has_doc or self.get_attr(member, "has_doc_section", False)
            # GetAccess applies when Access is not given; an event's is ListenAccess
            level = (
                access_of(member, "Access")
                or access_of(member, "GetAccess")
                or access_of(member, "ListenAccess")
            )
            classes = access_list(level)
            # (the option that keeps a restricted member, names in that option)
            if not want_all:
                rule = None
            elif level in ("private", "protected"):
                rule = (getattr(self.options, f"{level}_members"), [membername])
            elif access_of(member, "Hidden"):
                rule = (self.options.hidden_members, [membername])
            elif classes is not None:
                rule = (access_lists, classes)
            else:
                rule = None
            if rule is not None:
                # ``:option:`` alone keeps all; with names, the named ones
                option, names = rule
                listed = option is ALL or any(n in (option or ()) for n in names)
                keep = listed and (has_doc or bool(self.options.undoc_members))
            else:
                # ignore undocumented members if :undoc-members: is not given
                keep = (
                    has_doc
                    or bool(self.options.undoc_members)
                    or isinstance(member, MatEnumeration)
                )

            # give the user a chance to decide whether this member
            # should be skipped
            skip_user = self.env.events.emit_firstresult(
                "autodoc-skip-member",
                self.objtype,
                membername,
                member,
                not keep,
                self.options,
            )
            if skip_user is not None:
                keep = not skip_user

            if keep:
                ret.append((membername, member, isattr))
        return ret

    def document_members(self, all_members=False):
        """Generate reST for member documentation.

        If *all_members* is True, do all members, else those given by
        *self.options.members*.
        """
        want_all = all_members or self.options.members is ALL
        # find out which members are documentable
        _, members = self.get_object_members(want_all)

        # remove members given by exclude-members
        if self.options.exclude_members:
            members = [
                (membername, member)
                for (membername, member) in members
                if membername not in self.options.exclude_members
            ]

        # document non-skipped members
        memberdocumenters = []
        for mname, member, isattr in self.filter_members(members, want_all):
            classes = []
            for name, cls in self.documenters.items():
                if name.startswith("mat:") and cls.can_document_member(
                    member, mname, isattr, self
                ):
                    classes.append(cls)
            if not classes:
                # don't know how to document this member
                continue
            # prefer the documenter with the highest priority
            classes.sort(key=lambda cls: cls.priority)
            # members are named by path reference: files of a folder, or
            # members of a class
            if isinstance(self.object, MatModule):
                full_mname = getattr(member, "ref", None) or mat_naming.join_reference(
                    self.ref, mname
                )
            elif isinstance(self.object, MatLibrary):
                full_mname = f"{self.ref}/{mname}"
            else:
                full_mname = f"{self.ref}.{mname}"
            documenter = classes[-1](self.directive, full_mname, self.indent)
            documenter.source_tag = ".".join([*self.objpath, mname])
            memberdocumenters.append((documenter, isattr))
        member_order = self.options.member_order or self.env.config.autodoc_member_order
        if member_order == "groupwise":
            # sort by group; relies on stable sort to keep items in the
            # same group sorted alphabetically
            memberdocumenters.sort(key=lambda e: e[0].member_order)
        elif member_order == "bysource" and self.analyzer:
            # sort by source order, by virtue of the module analyzer
            tagorder = self.analyzer.tagorder

            def keyfunc(entry):
                return tagorder.get(entry[0].source_tag, len(tagorder))

            memberdocumenters.sort(key=keyfunc)

        for documenter, _ in memberdocumenters:
            documenter.generate(all_members=True, real_modname=self.real_modname)

    def generate(
        self,
        more_content=None,
        real_modname=None,
        check_module=False,  # noqa: ARG002 - members are always in their folder
        all_members=False,
    ):
        """Generate reST for the object given by *self.name*, and possibly for
        its members.

        If *more_content* is given, include that content. If *real_modname* is
        given, use that module name to find the source order of members. If
        *all_members* is True, document all members.
        """
        if not self.parse_name():
            # parse_name warned
            return

        # now, get the object to document (parse_name resolved it)
        self.import_object()

        # If there is no real module defined, figure out which to use.
        # The real module is used in the module analyzer to look up the module
        # where the attribute documentation would actually be found in.
        # This is used for situations where you have a module that collects the
        # functions and classes of internal submodules.
        self.real_modname = real_modname or self.get_real_modname()

        # the source order of members (``:member-order: bysource``)
        try:
            self.analyzer = MatModuleAnalyzer.for_module(self.real_modname)
        except MatcodeError as err:
            logger.debug("[sphinxcontrib-matlabdomain] module analyzer failed: %s", err)
            self.analyzer = None
        # Source files are dependencies through the domain (doc_sources).

        # make sure that the result starts with an empty line.  This is
        # necessary for some situations where another directive preprocesses
        # reST and no starting newline is present
        self.add_line("", "<autodoc>")

        # format the object's signature, if any
        sig = self.format_signature()

        # generate the directive header and options, if applicable
        self.add_directive_header(sig)
        self.add_line("", "<autodoc>")

        # e.g. the module directive doesn't have content
        self.indent += self.content_indent

        # add all content (from docstrings, attribute docs etc.)
        self.add_content(more_content)

        # document members, if possible
        self.document_members(all_members)


class MatFolderDocumenter(MatlabDocumenter, PyModuleDocumenter):
    objtype = "folder"
    accepts = staticmethod(is_folder_object)
    # Members share the options, so the class options apply to their members.
    option_spec = {
        **MEMBER_OPTIONS,
        "synopsis": identity,
        "platform": identity,
        "deprecated": bool_option,
    }

    def parse_name(self):
        ret = MatlabDocumenter.parse_name(self)
        if self.args or self.retann:
            logger.warning(
                (
                    "[sphinxcontrib-matlabdomain] "
                    "signature arguments or return annotation given for autofolder %s"
                ),
                self.fullname,
                type="mat",
                subtype="directive",
            )
        return ret

    def add_directive_header(self, sig):  # noqa: ARG002
        sourcename = self.get_sourcename()
        self.add_line(f".. {self.domain}:folder:: {self.ref}", sourcename)
        if self.options.no_index or self.options.noindex:
            self.add_line("   :noindex:", sourcename)

        # add some folder-specific options
        if self.options.synopsis:
            self.add_line(f"   :synopsis: {self.options.synopsis}", "<autodoc>")
        if self.options.platform:
            self.add_line(f"   :platform: {self.options.platform}", "<autodoc>")
        if self.options.deprecated:
            self.add_line("   :deprecated:", "<autodoc>")

    def get_object_members(self, want_all):
        if want_all:
            # A file is listed before a folder with the same name; special
            # files are documented only when named (and not parsed here).
            members = {}
            for name, ref in self.object.member_refs():
                if not is_hidden(ref):
                    members.setdefault(name, []).append(ref)
            dom = self.env.get_domain("mat")
            # sorted like class members, not in the file system's listing order
            return False, [
                (n, resolve(dom, min(refs, key=lambda r: r[-1:] == "/")))
                for n, refs in sorted(members.items())
            ]
        else:
            memberlist = self.options.members or []

        ret = []
        for mname in memberlist:
            if attr := self.get_attr(self.object, mname, None):
                ret.append((mname, attr))
            else:
                logger.warning(
                    "[sphinxcontrib-matlabdomain] missing attribute mentioned"
                    " in :members: or __all__: folder %s, attribute %s",
                    safe_getattr(self.object, "__name__", "???"),
                    mname,
                    type="mat",
                    subtype="not_found",
                )
        return False, ret


class MatModuleLevelDocumenter(MatlabDocumenter):
    """Specialized Documenter subclass for objects on folder level (functions,
    classes, data/constants).
    """


class MatClassLevelDocumenter(MatlabDocumenter):
    """Specialized Documenter subclass for objects on class level (methods,
    attributes). A bare member name is looked up in the current class first.
    """

    class_level = True


class MatDocstringSignatureMixin(MatlabDocumenter):
    """Mixin for FunctionDocumenter and MethodDocumenter to provide the
    feature of reading the signature from the docstring.
    """

    def _find_signature(self):
        docstrings = MatlabDocumenter.get_doc(self)
        # not ``[[]]`` either: help of blank ``%`` lines prepares to no lines
        if len(docstrings) != 1 or not docstrings[0]:
            return
        doclines = docstrings[0]
        setattr(self, "__new_doclines", doclines)
        # match first line of docstring against signature RE
        match = mat_ext_sig_re.match(doclines[0])
        if not match:
            return
        _, _, base, args, retann = match.groups()
        # the base name must match ours
        if not self.objpath or base != self.objpath[-1]:
            return
        # re-prepare docstring to ignore indentation after signature
        docstrings = MatlabDocumenter.get_doc(self)
        doclines = docstrings[0]
        # ok, now jump over remaining empty lines and set the remaining
        # lines as the new doclines
        i = 1
        while i < len(doclines) and not doclines[i].strip():
            i += 1
        setattr(self, "__new_doclines", doclines[i:])
        return args, retann

    def get_doc(self):
        lines = getattr(self, "__new_doclines", None)
        if lines is not None:
            return [lines]
        return MatlabDocumenter.get_doc(self)

    def format_signature(self):
        if self.args is None and self.env.config.autodoc_docstring_signature:
            # only act if a signature is not explicitly given already, and if
            # the feature is enabled
            result = self._find_signature()
            if result is not None:
                self.args, self.retann = result
        return MatlabDocumenter.format_signature(self)


class MatFunctionDocumenter(MatDocstringSignatureMixin, MatModuleLevelDocumenter):
    """Specialized Documenter subclass for functions."""

    objtype = "function"
    member_order = 30

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatFunction)

    def format_args(self):
        # a placeholder for an unreadable file is a script without args
        if getattr(self.object, "args", None):
            return "(" + ", ".join(self.object.args) + ")"

    def document_members(self, all_members=False):
        pass


def make_baseclass_links(env, obj):
    """Return list of base class links."""
    # not a MatClass when the file failed to read or parse as a class
    obj_bases = getattr(obj, "__bases__", None) or {}
    links = []
    if len(obj_bases):
        base_classes = obj_bases.items()
        for base_class_name, entity in base_classes:
            if not entity:
                links.append(f":mat:class:`{base_class_name}`")
            else:
                links.append(entity.link(env))

    return links


class MatClassDocumenter(MatModuleLevelDocumenter):
    """Specialized Documenter subclass for classes."""

    objtype = "class"
    member_order = 20
    option_spec = MEMBER_OPTIONS

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatClass)

    def format_args(self):
        """Format arguments.

        We use the method named the same as the class for arguments, but we only
        renders the arguments if `matlab_class_signature` is True and the method
        exist.
        """
        ctor = self._constructor()
        if ctor is None or not self.env.config.matlab_class_signature:
            return None
        if ctor.args:
            return "(" + ", ".join(ctor.args) + ")"

    def _constructor(self):
        """Return the method named like the class, or None."""
        ctor = self.get_attr(self.object, self.object.name, None)
        return ctor if isinstance(ctor, MatMethod) else None

    def _constructor_documenter(self, ctor):
        """Return a method documenter of ``ctor`` and its docstring signature."""
        init_doc = MatMethodDocumenter(self.directive, self.object.name)
        init_doc.object = ctor
        init_doc.objpath = [self.object.name]
        return init_doc, init_doc._find_signature()

    def format_signature(self):
        # get constructor method signature from docstring
        ctor = self._constructor()
        if ctor is not None and self.env.config.autodoc_docstring_signature:
            # only act if the feature is enabled
            _, result = self._constructor_documenter(ctor)
            if result is not None:
                # use args only for Class signature
                return f"({result[0]})"

        return MatModuleLevelDocumenter.format_signature(self)

    def add_directive_header(self, sig):
        MatlabDocumenter.add_directive_header(self, sig)
        # an unreadable file's placeholder has no attributes
        self.add_flags(
            getattr(self.object, "attrs", {}),
            (("abstract", "Abstract"), ("sealed", "Sealed")),
        )

        # add inheritance info, if wanted
        if self.options.show_inheritance:
            self.add_line("", "<autodoc>")
            if base_class_links := make_baseclass_links(self.env, self.object):
                self.add_line(
                    _("   Bases: %s") % ", ".join(base_class_links), "<autodoc>"
                )

    def get_doc(self):
        content = self.env.config.autoclass_content

        docstrings = []
        if attrdocstring := self.get_attr(self.object, "__doc__", None):
            docstrings.append(attrdocstring)

        # for classes, what the "docstring" is can be controlled via a
        # config value; the default is only the class docstring
        ctor = self._constructor()
        if content in ("both", "init") and ctor is not None:
            if self.env.config.autodoc_docstring_signature:
                # without the signature line
                init_doc, _ = self._constructor_documenter(ctor)
                initdocstring = "\n".join(
                    ["\n".join(line) for line in (init_doc.get_doc() or [])]
                )
            else:
                initdocstring = ctor.docstring
            if initdocstring:
                if content == "init":
                    docstrings = [initdocstring]
                else:
                    docstrings.append(initdocstring)

        doc = [prepare_docstring(x) for x in docstrings]

        return doc

    def help_sources(self):
        sources = super().help_sources()
        # ``autoclass_content`` may add the constructor's help
        if (ctor := self._constructor()) is not None:
            sources.append((ctor.docstring, ctor.docstring_line))
        return sources

    def class_object(self):
        # the associated MatClass object
        return self.object

    def auto_link_basic(self, docstrings):
        docstrings = MatlabDocumenter.auto_link_basic(self, docstrings)
        return self.auto_link_class_members(docstrings)

    def auto_link_class_members(self, docstrings):
        # auto link property and method names in class docstring
        prop_re = re.compile(r"(.* Properties:)", re.IGNORECASE)
        meth_re = re.compile(r"(.* Methods:)", re.IGNORECASE)
        is_prop_line = False
        is_meth_line = False
        for i in range(len(docstrings)):
            for j in range(len(docstrings[i])):
                if line := docstrings[i][j]:
                    if prop_re.search(line):  # line ends with "Properties:"
                        is_prop_line = True
                        is_meth_line = False
                    elif meth_re.search(line):  # line ends with "Methods:"
                        is_prop_line = False
                        is_meth_line = True
                    elif is_prop_line:
                        # auto-link first word to corresponding property, if it exists
                        docstrings[i][j] = self.link_member("attr", line)
                    elif is_meth_line:
                        # auto-link first word to corresponding method, if it exists
                        docstrings[i][j] = self.link_member("meth", line)
                elif is_prop_line:  # blank line following properties section
                    is_prop_line = False  # end properties section
                elif is_meth_line:  # blank line following methods section
                    is_meth_line = False  # end methods section

        return docstrings

    def link_member(self, type, line):
        parens = "()" if type == "meth" else ""
        p = re.compile(r"((\*\s*)?(\b\w*\b))(?=\s*-)")
        if match := p.search(line):
            name = match[3]
            link = (
                f"* :mat:{type}:`{name}{parens} "
                f"<{self.object.fullname(self.env)}.{name}>`"
            )
            line = p.sub(lambda _: link, line, 1)
        return line

    def auto_link_all(self, docstrings):
        docstrings = self.auto_link_methods(self.object, docstrings)
        return MatlabDocumenter.auto_link_all(self, docstrings)

    def document_members(self, all_members=False):
        want_all = all_members or self.options.members is ALL
        # find out which members are documentable
        _, members = self.get_object_members(want_all)

        # use filtered members to check for empty sections
        filtered_members = [
            (membername, member)
            for (membername, member, isattr) in self.filter_members(members, want_all)
        ]

        # create list of properties
        prop_names = [
            membername
            for (membername, member) in filtered_members
            if isinstance(member, MatProperty)
        ]
        # create list of constructors
        if self.env.config.autoclass_content in ("both", "init"):
            # skip constructor section,
            # since its docstring has already been used for the class
            cons_names = []
        else:
            cons_names = [
                membername
                for (membername, member) in filtered_members
                if isinstance(member, MatMethod) and member.name == member.cls.name
            ]
        # create list of non-constructor methods
        meth_names = [
            membername
            for (membername, member) in filtered_members
            if isinstance(member, MatMethod) and member.name != member.cls.name
        ]
        # create list of enums
        enum_names = [
            membername
            for (membername, member) in filtered_members
            if isinstance(member, MatEnumeration)
        ]
        event_names = [
            membername
            for (membername, member) in filtered_members
            if isinstance(member, MatEvent)
        ]
        # (a class has no other members)
        # create list of members that are not properties
        non_properties = [
            membername
            for (membername, member) in members
            if not isinstance(member, MatProperty)
        ]
        # create list of members that are not constructors
        non_constructors = [
            membername
            for (membername, member) in members
            if not isinstance(member, MatMethod) or member.name != member.cls.name
        ]
        # create list of members that are not non-constructor methods
        non_methods = [
            membername
            for (membername, member) in members
            if not isinstance(member, MatMethod) or member.name == member.cls.name
        ]
        # create list of members that are not properties
        non_enums = [
            membername
            for (membername, member) in members
            if not isinstance(member, MatEnumeration)
        ]
        non_events = [
            membername
            for (membername, member) in members
            if not isinstance(member, MatEvent)
        ]

        # container
        if cons_names or prop_names or enum_names or meth_names or event_names:
            self.add_line("", "<autodoc>")
            self.add_line(".. container:: members", "<autodoc>")
            self.add_line("", "<autodoc>")
            self.indent += "   "

        # constructor
        if cons_names:
            self.document_member_section(
                "Constructor Summary", non_constructors, all_members
            )

        # properties
        if prop_names:
            self.document_member_section(
                "Property Summary", non_properties, all_members
            )

        # enumss
        if enum_names:
            self.document_member_section("Enumeration Values", non_enums, all_members)

        # methods
        if meth_names:
            self.document_member_section("Method Summary", non_methods, all_members)

        if event_names:
            self.document_member_section("Event Summary", non_events, all_members)

    def document_member_section(self, heading, new_excludes, all_members):
        # save up original indent and exclude_members
        indent = self.indent
        exclude_members = self.options.exclude_members or []

        # output heading and section content
        self.add_line(heading, "<autodoc>")
        self.indent += "   "
        self.add_line(".. ", "<autodoc>")  # a comment, to force a <dd> in the HTML
        if exclude_members is EMPTY:
            self.options.exclude_members = set(new_excludes)
        else:
            self.options.exclude_members = set(list(exclude_members) + new_excludes)
        MatModuleLevelDocumenter.document_members(self, all_members)

        # restore original indent and exclude_members
        self.indent = indent
        self.options.exclude_members = exclude_members


class MatDataDocumenter(MatModuleLevelDocumenter, PyDataDocumenter):
    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatScript)


class MatMethodDocumenter(MatDocstringSignatureMixin, MatClassLevelDocumenter):
    """Specialized Documenter subclass for methods (normal, static and class)."""

    objtype = "method"
    member_order = 50
    priority = 1  # must be more than FunctionDocumenter

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatMethod)

    def import_object(self):
        ret = MatClassLevelDocumenter.import_object(self)
        if self.object.attrs.get("Static"):
            self.directivetype = "staticmethod"
            # document class and static members before ordinary ones
            self.member_order = self.member_order - 1
        else:
            self.directivetype = "method"
        return ret

    def add_directive_header(self, sig):
        super().add_directive_header(sig)
        self.add_flags(
            self.object.attrs, (("abstract", "Abstract"), ("sealed", "Sealed"))
        )

    def format_args(self):
        """Format argument.

        We omit `obj` and `self` from the output if they are the first argument
        unless it's a class constructor or a static method (which has no object).

        Rendering -> "(arg1, arg2, arg3)"

        """
        is_ctor = self.object.cls.name == self.object.name
        is_static = bool(self.object.attrs.get("Static"))

        if self.object.args:
            arglist = list(self.object.args.keys())
            if arglist[0] in ("obj", "self") and not (is_ctor or is_static):
                return "(" + ", ".join(arglist[1:]) + ")"
            else:
                return "(" + ", ".join(arglist) + ")"

    def document_members(self, all_members=False):
        pass

    def class_object(self):
        # the associated MatClass object
        return self.object.cls

    def auto_link_self(self, docstrings):
        name = self.object.name
        # negative look-behind for ` . < @ * / | or <non-breaking space>
        # and negative look-ahead for ` * / | or <non-breaking space> or .<alphanum>
        p = re.compile(
            r"(?<!(`|\.|<|@|\*| |/|\|))\b" + name + r"\b(?!`|\*| |\.\w|/|\|)"
        )
        no_link_state = 0  # normal mode (no literal block detected)
        for i in range(len(docstrings)):
            for j in range(len(docstrings[i])):
                not_in_literal_block, no_link_state = self.detect_literal_block(
                    docstrings[i][j], no_link_state
                )
                if not_in_literal_block and docstrings[i][j]:  # also not blank line
                    if _ := p.search(docstrings[i][j]):
                        link = (
                            f":mat:meth:`{name}() "
                            f"<{self.class_object().fullname(self.env)}.{name}>`"
                        )
                        docstrings[i][j] = p.sub(
                            lambda m, t=link: _inline(m, t), docstrings[i][j]
                        )
        return docstrings

    def auto_link_all(self, docstrings):
        docstrings = self.auto_link_methods(self.object.cls, docstrings)
        docstrings = self.auto_link_self(docstrings)
        return MatlabDocumenter.auto_link_all(self, docstrings)


def is_read_only(attrs):
    """Return True for a property whose set access is stricter than its read
    access (``SetAccess = private``, ``immutable``, ...); not for constants.
    """

    def level(*names):
        for name in names:
            if (value := attrs.get(name)) is not None:
                return value.strip("'\"") if isinstance(value, str) else value
        return "public"

    if attrs.get("Constant"):
        return False
    setter = level("SetAccess", "Access")
    return setter != "public" and setter != level("GetAccess", "Access")


class MatAttributeDocumenter(MatClassLevelDocumenter):
    """Specialized Documenter subclass for attributes (properties and
    enumeration values).
    """

    objtype = "attribute"
    member_order = 60
    option_spec = dict(MatModuleLevelDocumenter.option_spec)
    option_spec["annotation"] = annotation_option

    # must be higher than the MethodDocumenter, else it will recognize
    # some non-data descriptors as methods
    priority = 10

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, (MatProperty, MatEnumeration))

    def document_members(self, all_members=False):
        pass

    def import_object(self):
        ret = MatClassLevelDocumenter.import_object(self)
        # only properties have a default value and specs
        self._datadescriptor = not isinstance(self.object, MatProperty)
        return ret

    def get_real_modname(self):
        return (
            self.get_attr(self.parent or self.object, "__module__", None)
            or self.modname
        )

    def add_directive_header(self, sig):
        MatClassLevelDocumenter.add_directive_header(self, sig)
        if isinstance(self.object, MatProperty):
            attrs = self.object.attrs
            self.add_flags(
                {**attrs, "read-only": is_read_only(attrs)},
                (
                    ("abstract", "Abstract"),
                    ("constant", "Constant"),
                    ("dependent", "Dependent"),
                    ("read-only", "read-only"),
                ),
            )
        if not self.options.annotation:
            if isinstance(self.object, MatEnumeration):
                # its constructor arguments
                args = self.object.args
                if args and self.env.config.matlab_show_property_default_value:
                    self.add_line(f"   :annotation: ({', '.join(args)})", "<autodoc>")
            elif not self._datadescriptor:
                obj_default = ""
                if self.env.config.matlab_show_property_default_value:
                    obj_default = self.object.default
                if obj_default is None:
                    obj_default = ""
                # Multi-line default values are truncated to the first part
                # and postfixed with an ellipsis.
                if "\n" in obj_default:
                    obj_default_parts = obj_default.split("\n")
                    obj_default = f"{obj_default_parts[0]} ... {obj_default_parts[-1]}"

                if obj_default:
                    obj_default = f" = {obj_default}"

                if self.env.config.matlab_show_property_specs:
                    prop_spec = ""
                    if self.object.size is not None:
                        prop_spec = f"{prop_spec}(" + ",".join(self.object.size) + ")"
                    if self.object.type is not None:
                        prop_spec = f"{prop_spec} {self.object.type}"
                    if self.object.validators is not None:
                        prop_spec = (
                            prop_spec + " {" + ",".join(self.object.validators) + "}"
                        )
                    obj_default = prop_spec + obj_default

                self.add_line(f"   :annotation: {obj_default}", "<autodoc>")
        elif self.options.annotation is SUPPRESS:
            pass
        else:
            self.add_line(f"   :annotation: = {self.options.annotation}", "<autodoc>")

    def add_content(self, more_content, no_docstring=False):
        # if not self._datadescriptor:
        #     # if it's not a data descriptor, its docstring is very probably the
        #     # wrong thing to display
        MatClassLevelDocumenter.add_content(self, more_content, no_docstring)

    def class_object(self):
        # the associated MatClass object
        return self.object.cls

    def auto_link_self(self, docstrings):
        name = self.object.name
        # negative look-behind for ` . < * / | or <non-breaking space>
        # and negative look-ahead for ` * / | or <non-breaking space>
        p = re.compile(r"(?<!(`|\.|<|\*| |/|\|))\b" + name + r"\b(?!`|\*| |/|\|)")
        no_link_state = 0  # normal mode (no literal block detected)
        for i in range(len(docstrings)):
            for j in range(len(docstrings[i])):
                not_in_literal_block, no_link_state = self.detect_literal_block(
                    docstrings[i][j], no_link_state
                )
                if (
                    not_in_literal_block
                    and docstrings[i][j]
                    and p.search(docstrings[i][j])
                ):
                    link = (
                        f":mat:attr:`{name} "
                        f"<{self.class_object().fullname(self.env)}.{name}>`"
                    )
                    docstrings[i][j] = p.sub(
                        lambda m, t=link: _inline(m, t), docstrings[i][j]
                    )
        return docstrings

    def auto_link_all(self, docstrings):
        docstrings = self.auto_link_methods(self.object.cls, docstrings)
        docstrings = self.auto_link_self(docstrings)
        return MatlabDocumenter.auto_link_all(self, docstrings)


class MatEventDocumenter(MatClassLevelDocumenter):
    """Specialized Documenter subclass for events."""

    objtype = "event"
    member_order = 70
    option_spec = dict(MatModuleLevelDocumenter.option_spec)

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatEvent)

    def document_members(self, all_members=False):
        pass

    def class_object(self):
        # the associated MatClass object
        return self.object.cls

    def auto_link_all(self, docstrings):
        docstrings = self.auto_link_methods(self.object.cls, docstrings)
        return MatlabDocumenter.auto_link_all(self, docstrings)


class MatScriptDocumenter(MatModuleLevelDocumenter):
    """Specialized Documenter subclass for scripts."""

    objtype = "script"

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatScript)

    def document_members(self, all_members=False):
        pass


class MatApplicationDocumenter(MatModuleLevelDocumenter):
    """Specialized Documenter subclass for Matlab Applications (.mlapp)."""

    objtype = "application"

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, MatApplication)

    def document_members(self, all_members=False):
        pass


#: metadata of a Simulink file (``matlab_simulink_metadata``) -> its label
SIMULINK_METADATA = {
    "release": _("Release"),
    "model_version": _("Model version"),
    "creator": _("Created by"),
    "created": _("Created"),
    "last_modified_by": _("Last modified by"),
    "modified": _("Last modified"),
}
_PORT_KINDS = {
    "Inport": _("input"),
    "Outport": _("output"),
    "PMIOPort": _("connection"),
    "EnablePort": _("enable"),
    "TriggerPort": _("trigger"),
    "ActionPort": _("action"),
}
# Port settings Simulink leaves to inheritance: shown as empty cells.
_PORT_UNSET = {"data_type": "Inherit: auto", "dimensions": "-1", "unit": "inherit"}
_PORT_COLUMNS = (
    ("data_type", _("Data type")),
    ("dimensions", _("Dimensions")),
    ("unit", _("Unit")),
    ("description", _("Description")),
)


def metadata_option(arg):
    """``:metadata: release, creator``: the metadata to show (none if empty)."""
    return [key.strip() for key in (arg or "").split(",") if key.strip()]


def _literal(text):
    """``text`` as reST that shows it as it is, in code font."""
    text = " ".join(text.split())
    if text and "`" not in text:
        return f"``{text}``"
    return _escaped(text)


def _escaped(text):
    """``text`` as reST that shows it as it is."""
    return re.sub(r"([^\w\s])", r"\\\1", " ".join(text.split()))


def _block(first, text, indent):
    """Lines of ``first`` followed by the lines of reST ``text``, indented."""
    lines = text.strip().splitlines() or [""]
    return [
        f"{first}{lines[0]}".rstrip(),
        *(f"{indent}{line}".rstrip() for line in lines[1:]),
    ]


#: the comment that the Simulink directive replaces with the documentation file
SIMULINK_DOC_PLACEHOLDER = "sphinxcontrib-matlabdomain: Simulink documentation file"

#: options of every Simulink documenter
_SIMULINK_OPTIONS = {
    **MatlabDocumenter.option_spec,
    "hidden-mask-parameters": bool_option,
    "metadata": metadata_option,
}
#: reference kind -> (label, role)
_REFERENCE_KINDS = {
    "model": (_("model reference"), "simulink_model"),
    "subsystem": (_("subsystem reference"), "simulink_subsystem_reference"),
    "library": (_("library link"), "simulink_library_block"),
}
_SIMULINK_NAME = re.compile(r"[A-Za-z]\w*")


class MatSimulinkDocumenter(MatModuleLevelDocumenter):
    """Documenter of a Simulink model; the base of the other Simulink
    documenters. Shows the description, the mask (type, help, parameters),
    the ports and the metadata of ``matlab_simulink_metadata``.
    """

    objtype = "simulink_model"
    # The argument is the whole name: block names may hold parentheses.
    name_pattern = re.compile(r"\s*(.+?)\s*((?!))?((?!))?\Z", re.DOTALL)
    option_spec = {
        **_SIMULINK_OPTIONS,
        "references": bool_option,
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.accepts = staticmethod(simulink_accepts(SIMULINK_CLASSES[cls.objtype]))

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):  # noqa: ARG003 - required by Sphinx API
        return isinstance(member, SIMULINK_CLASSES[cls.objtype])

    def format_name(self):
        return self.display.replace("\n", " ")

    def format_signature(self, **kwargs):  # noqa: ARG002
        return ""

    def add_directive_header(self, sig):  # noqa: ARG002
        sourcename = self.get_sourcename()
        self.add_line(f".. mat:{self.objtype}:: {self.format_name()}", sourcename)
        if self.options.no_index or self.options.noindex:
            self.add_line("   :noindex:", sourcename)
        ref = self.ref
        # An option value is one line without surrounding space.
        if "\n" in ref or ref != ref.strip() or ref[:1] == '"':
            ref = json.dumps(ref, ensure_ascii=False)
        self.add_line(f"   :reference: {ref}", sourcename)

    def document_members(self, all_members=False):
        pass

    def add_content(self, more_content, no_docstring=False):
        super().add_content(None, no_docstring)
        sourcename = self.get_sourcename()
        # The directive puts the Simulink documentation file here.
        self.add_line("", sourcename)
        self.add_line(f".. {SIMULINK_DOC_PLACEHOLDER}", sourcename)
        self.add_line("", sourcename)
        if more_content:
            for line, src in zip(more_content.data, more_content.items, strict=False):
                self.add_line(line, src[0], src[1])
        for line in self.simulink_lines():
            self.add_line(line, sourcename)

    def simulink_parts(self):
        """Return ``(mask, ports, metadata)`` of the object."""
        obj = self.object
        if isinstance(obj, MatBlock):
            return obj.block.mask, obj.block.ports, ()
        diagram = cast(MatSimulinkFile, obj).diagram
        if diagram is None:  # a placeholder: the file could not be read
            return None, (), ()
        return diagram.system_mask, diagram.ports, diagram.metadata

    def simulink_lines(self):
        """Return the reST of the mask, ports and metadata."""
        mask, ports, metadata = self.simulink_parts()
        fields = []
        if mask is not None:
            if mask.type:
                fields.append(f":{_('Mask type')}: {_literal(mask.type)}")
            if mask.description and mask.description != self.object.docstring:
                fields += _block(f":{_('Mask description')}: ", mask.description, "   ")
            fields += self.help_lines(mask)
        fields += self.metadata_lines(metadata)
        lines = ["", *fields, ""] if fields else [""]
        if mask is not None:
            lines += self.mask_parameter_lines(mask.parameters)
        return lines + self.port_lines(ports) + self.reference_lines()

    def reference_lines(self):
        """Return the list of the model references, subsystem references and
        library links of the file (``:references:``), each a link to its
        target; one outside the project stays text.
        """
        diagram = getattr(self.object, "diagram", None)
        if not self.options.get("references") or diagram is None:
            return []
        lines = []
        for ref in diagram.references:
            label, role = _REFERENCE_KINDS[ref.kind]
            target = " ".join(ref.target.split())
            if ref.kind != "library":
                target = re.sub(r"\.(slx|mdl)$", "", target)
            if ref.kind == "library" or _SIMULINK_NAME.fullmatch(target):
                link = f":mat:{role}:`{target}`"
            else:  # not set, or a variable name in the dialog
                link = _literal(target)
            block = _literal(" ".join(ref.block.split()))
            lines.append(f"* {block} ({label}): {link}")
        if not lines:
            return []
        return [f".. rubric:: {_('References')}", "", *lines, ""]

    def help_lines(self, mask):
        """Return the mask Help: a link for a URL, ``web(...)`` or a linker line
        to another object (one to this object is left out), else its text.
        """
        text = mask.help
        if not text.strip():
            return []
        shown = (self.object.docstring or "", mask.description)
        if " ".join(text.split()) in {" ".join(t.split()) for t in shown}:
            return []  # the same text as the description
        label = f":{_('Help')}: "
        target = mat_simulink.help_target(text)
        if target is None:
            return _block(label, text, "   ")
        kind, value = target
        if kind == "url":
            return [f"{label}`{value} <{value}>`__"]
        if same_block(value, self.ref):
            return []
        # A role's target writes a line break in a block name as a space.
        return [f"{label}:mat:obj:`{' '.join(value.split())}`"]

    def metadata_lines(self, metadata):
        keys = self.options.metadata
        if keys is None:
            keys = self.env.config.matlab_simulink_metadata
        values = dict(metadata)
        lines = []
        for key in keys:
            if key not in SIMULINK_METADATA:
                logger.warning(
                    "[sphinxcontrib-matlabdomain] unknown Simulink metadata %r; "
                    "known: %s",
                    key,
                    ", ".join(SIMULINK_METADATA),
                    type="mat",
                    subtype="simulink",
                    location=(self.env.docname, self.directive.lineno),
                )
            elif values.get(key):
                text = _escaped(values[key])
                lines.append(f":{SIMULINK_METADATA[key]}: {text}")
        return lines

    def mask_parameter_lines(self, parameters):
        """Return the mask parameters, like the input arguments of a function;
        hidden ones only with ``:hidden-mask-parameters:``.
        """
        lines = []
        for p in parameters:
            if not (p.visible or self.options.hidden_mask_parameters) or not p.name:
                continue
            prompt = " ".join(p.prompt.split())
            if prompt and prompt[-1] not in ".?!:":
                prompt += "."
            details = [prompt] if prompt else []
            if p.value:
                details.append(_("Default: %s.") % _literal(p.value))
            if p.options:
                choices = ", ".join(_literal(o) for o in p.options)
                details.append(_("Options: %s.") % choices)
            lines += _block(f":maskparam {p.name}: ", " ".join(details), "   ")
            if p.type:
                lines.append(f":maskparamtype {p.name}: {p.type}")
        return [*lines, ""] if lines else []

    def port_lines(self, ports):
        """Return the ports as a table, with the columns that have a value."""
        if not ports:
            return []

        def value(port, key):
            text = getattr(port, key)
            return "" if text == _PORT_UNSET.get(key) else text

        columns = [
            (key, title)
            for key, title in _PORT_COLUMNS
            if any(value(port, key) for port in ports)
        ]
        lines = [
            f".. rubric:: {_('Ports')}",
            "",
            ".. list-table::",
            "   :header-rows: 1",
            "",
            f"   * - {_('Port')}",
            f"     - {_('Name')}",
            *(f"     - {title}" for _key, title in columns),
        ]
        for port in ports:
            # a bus element port: port.element
            name = ".".join(filter(None, (port.port_name, port.element))) or port.name
            kind = _PORT_KINDS.get(port.block_type, port.block_type)
            lines.append(f"   * - {kind} {port.number}".rstrip())
            lines.append(f"     - {_literal(name)}")
            for key, _title in columns:
                text = value(port, key)
                if key == "description":
                    lines += _block("     - ", text, "       ")
                else:
                    lines.append(f"     - {_literal(text)}".rstrip())
        return [*lines, ""]


class MatSimulinkLibraryDocumenter(MatSimulinkDocumenter):
    """Documenter of a Simulink library. With ``:members:``, its documented
    blocks follow in the library's order, then a list of its linked blocks
    (each a link to its source block) and sublibrary blocks (each a link to
    the library it opens).
    """

    objtype = "simulink_library"
    option_spec = {
        **_SIMULINK_OPTIONS,
        "members": members_option,
        "undoc-members": bool_option,
        "exclude-members": exclude_members_option,
    }

    def _wanted(self, blocks, want_all):
        """Return the blocks named by ``:members:`` (all if ``want_all``),
        without those of ``:exclude-members:``.
        """
        named = [] if want_all else list(self.options.members or ())
        excluded = self.options.exclude_members or ()

        def among(block, names):
            return any(same_block(block.path, name) for name in names)

        for name in named:
            if not any(same_block(block.path, name) for block in blocks):
                logger.warning(
                    "[sphinxcontrib-matlabdomain] %s has no documented block %r",
                    self.ref,
                    name,
                    type="mat",
                    subtype="not_found",
                    location=(self.env.docname, self.directive.lineno),
                )
        return [
            block
            for block in blocks
            if (want_all or among(block, named)) and not among(block, excluded)
        ]

    def get_object_members(self, want_all):
        library = cast(MatLibrary, self.object)
        blocks = library.diagram.library_blocks if library.diagram else ()
        sections = mat_sidecars.documented_blocks(self.env, self.ref)
        members = []
        for block in self._wanted(blocks, want_all):
            if block.mask is not None:
                member = MatBlock(block, library)
                member.has_doc_section = " ".join(block.path.split()) in sections
                members.append((block.path, member))
        return False, members

    def document_members(self, all_members=False):
        MatlabDocumenter.document_members(self, all_members)
        want_all = all_members or self.options.members is ALL
        if not (want_all or self.options.members):
            return
        library = cast(MatLibrary, self.object)
        blocks = library.diagram.library_blocks if library.diagram else ()
        items = []
        for block in self._wanted(blocks, want_all):
            if block.link:
                target = " ".join(block.link.split())
                items.append((block.path, f":mat:simulink_library_block:`{target}`"))
            elif block.opens:
                items.append((block.path, f":mat:simulink_library:`{block.opens}`"))
        if not items:
            return
        sourcename = self.get_sourcename()
        self.add_line("", sourcename)
        self.add_line(f".. rubric:: {_('Links to other blocks')}", sourcename)
        self.add_line("", sourcename)
        for path, link in items:
            self.add_line(f"* {_literal(path)}: {link}", sourcename)
        self.add_line("", sourcename)


class MatSimulinkSubsystemDocumenter(MatSimulinkDocumenter):
    """Documenter of a Simulink subsystem file (a Subsystem Reference's target)."""

    objtype = "simulink_subsystem_reference"


class MatSimulinkBlockDocumenter(MatSimulinkDocumenter):
    """Documenter of a block of a Simulink library."""

    objtype = "simulink_library_block"
    option_spec = _SIMULINK_OPTIONS


MatSimulinkDocumenter.accepts = staticmethod(
    simulink_accepts(SIMULINK_CLASSES[MatSimulinkDocumenter.objtype])
)
#: registered as ``mat:auto<objtype>``
SIMULINK_DOCUMENTERS = (
    MatSimulinkDocumenter,
    MatSimulinkLibraryDocumenter,
    MatSimulinkSubsystemDocumenter,
    MatSimulinkBlockDocumenter,
)
