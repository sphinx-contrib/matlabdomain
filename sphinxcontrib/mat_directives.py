from __future__ import unicode_literals
from sphinx.ext.autodoc.directive import AutodocDirective, DummyOptionSpec, DocumenterBridge
from sphinx.ext.autodoc.directive import process_documenter_options, parse_generated_content
from sphinx.util import logging
from sphinx import version_info

logger = logging.getLogger('matlab-domain')


class MatlabAutodocDirective(AutodocDirective):
    """A directive class for all MATLAB autodoc directives.

    Modified version of the Python AutodocDirective

    It works as a dispatcher of Documenters. It invokes a Documenter on running.
    After the processing, it parses and returns the generated content by
    Documenter.
    """
    option_spec = DummyOptionSpec()
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        reporter = self.state.document.reporter

        try:
            source, lineno = reporter.get_source_and_line(self.lineno)  # type: ignore
        except AttributeError:
            source, lineno = (None, None)
        logger.debug('[sphinxcontrib-matlabdomain] %s:%s: input:\n%s', source, lineno, self.block_text)

        # look up target Documenter
        objtype = self.name.replace('auto', '')  # Removes auto
        doccls = self.env.app.registry.documenters[objtype]

        # process the options with the selected documenter's option_spec
        try:
            documenter_options = process_documenter_options(doccls, self.config, self.options)
        except (KeyError, ValueError, TypeError) as exc:
            # an option is either unknown or has a wrong type
            logger.error('An option to %s is either unknown or has an invalid value: %s' %
                         (self.name, exc), location=(source, lineno))
            return []

        # generate the output
        if version_info[0] >= 2:
            params = DocumenterBridge(self.env, reporter, documenter_options, lineno, self.state)
        else:
            params = DocumenterBridge(self.env, reporter, documenter_options, lineno)
        documenter = doccls(params, self.arguments[0])
        documenter.generate(more_content=self.content)
        if not params.result:
            return []

        logger.debug('[sphinxcontrib-matlabdomain] output:\n%s', '\n'.join(params.result))

        # record all filenames as dependencies -- this will at least
        # partially make automatic invalidation possible
        for fn in params.filename_set:
            self.state.document.settings.record_dependencies.add(fn)

        result = parse_generated_content(self.state, params.result, documenter)
        return result
