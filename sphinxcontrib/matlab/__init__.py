# -*- coding: utf-8 -*-
"""
    sphinxcontrib
    ~~~~~~~~~~~~~

    This package is a namespace package that contains all extensions
    distributed in the ``sphinx-contrib`` distribution.

    :copyright: Copyright 2007-2009 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from .matlab import ensure_configuration, analyze, MATLABDomain
from . import mat_documenters as doc
from . import mat_directives


def setup(app):
    app.connect("config-inited", ensure_configuration)
    app.connect("builder-inited", analyze)

    app.add_domain(MATLABDomain)
    # autodoc
    app.add_config_value("matlab_src_dir", None, "env")
    app.add_config_value("matlab_src_encoding", None, "env")
    app.add_config_value("matlab_keep_package_prefix", False, "env")
    app.add_config_value("matlab_show_property_default_value", False, "env")
    app.add_config_value("matlab_show_property_specs", False, "env")
    app.add_config_value("matlab_short_links", False, "env")
    app.add_config_value("matlab_auto_link", None, "env")
    app.add_config_value("matlab_class_signature", False, "env")

    app.registry.add_documenter("mat:module", doc.MatModuleDocumenter)
    app.add_directive_to_domain(
        "mat", "automodule", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:function", doc.MatFunctionDocumenter)
    app.add_directive_to_domain(
        "mat", "autofunction", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:class", doc.MatClassDocumenter)
    app.add_directive_to_domain(
        "mat", "autoclass", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:method", doc.MatMethodDocumenter)
    app.add_directive_to_domain(
        "mat", "automethod", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:script", doc.MatScriptDocumenter)
    app.add_directive_to_domain(
        "mat", "autoscript", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:exception", doc.MatExceptionDocumenter)
    app.add_directive_to_domain(
        "mat", "autoexception", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:attribute", doc.MatAttributeDocumenter)
    app.add_directive_to_domain(
        "mat", "autoattribute", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:enum", doc.MatAttributeDocumenter)
    app.add_directive_to_domain(
        "mat", "autoenum", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:data", doc.MatDataDocumenter)
    app.add_directive_to_domain(
        "mat", "autodata", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:application", doc.MatApplicationDocumenter)
    app.add_directive_to_domain(
        "mat", "autoapplication", mat_directives.MatlabAutodocDirective
    )

    app.add_autodoc_attrgetter(doc.MatModule, doc.MatModule.getter)
    app.add_autodoc_attrgetter(doc.MatClass, doc.MatClass.getter)

    return {"parallel_read_safe": False}
