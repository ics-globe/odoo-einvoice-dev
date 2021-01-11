# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Web core module.
========================

This module provides the core of the Odoo Web Client.
    """,
    'depends': ['base'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
        'views/report_templates.xml',
        'views/base_document_layout_views.xml',
        'data/report_layout.xml',
    ],
    'assets': {
        #----------------------------------------------------------------------
        # MAIN BUNDLES
        #----------------------------------------------------------------------
        # These are the bundles meant to be called via "t-call-assets" in
        # regular XML templates.
        #
        # The convention to name bundles is as following:
        # 1) the module in which the bundle is first defined (check module
        #    order according to their dependencies), followed by a dot,
        # 2) an arbitrary name, relevant to the content of the bundle. Note
        #    that there is no need to put the "assets" keyword in the bundle
        #    name since it has already been explicited by the manifest key.
        #
        # Exemples:
        #   > web.common = assets common to the frontend and the backend, first
        #                  defined in the "web" module.
        #   > web_editor.wysiwyg = assets needed by components defined in the
        #                          "web_editor"  module, but never in "web".
        #
        # Note for backward compatibility:
        #   Most of the bundles have been renamed; since the parent key is
        #   already named "assets" there was no need to specify the "assets_"
        #   prefix anymore. Also the following bundles have been entirely
        #   renamed to reflect their purpose more accurately:
        #   - assets_tests    ->  test_tours

        'web.qweb': [
            'web/static/src/xml/base.xml',
            'web/static/src/xml/chart.xml',
            'web/static/src/xml/fields.xml',
            'web/static/src/xml/file_upload_progress_bar.xml',
            'web/static/src/xml/file_upload_progress_card.xml',
            'web/static/src/xml/kanban.xml',
            'web/static/src/xml/menu.xml',
            'web/static/src/xml/notification.xml',
            'web/static/src/xml/pivot.xml',
            'web/static/src/xml/rainbow_man.xml',
            'web/static/src/xml/report.xml',
            'web/static/src/xml/search_panel.xml',
            'web/static/src/xml/web_calendar.xml',
            'web/static/src/xml/graph.xml',
        ],
        'web.common_minimal_scripts': [
            'web/static/lib/es6-promise/es6-promise-polyfill.js',
            'web/static/src/js/promise_extension.js',
            'web/static/src/js/boot.js',
        ],
        'web.common': [
            ('include', 'web._base_variables'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._common_styles'),
            ('include', 'web.common_minimal_scripts'),
            ('include', 'web._common_scripts'),
        ],
        'web.common_lazy': [
            ('include', 'web._base_variables'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._common_styles'),
            ('include', 'web._common_scripts'),
        ],
        'web.backend': [
            ('include', 'web._base_variables'),
            ('include', 'web._backend_bootstrap_overrides'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._bootstrap'),

            'base/static/src/css/modules.css',

            ('include', 'web._backend_webclient'),

            'web/static/src/scss/webclient.scss',
            'web/static/src/scss/domain_selector.scss',
            'web/static/src/scss/model_field_selector.scss',
            'web/static/src/scss/progress_bar.scss',
            'web/static/src/scss/dropdown.scss',
            'web/static/src/scss/tooltip.scss',
            'web/static/src/scss/switch_company_menu.scss',
            'web/static/src/scss/debug_manager.scss',
            'web/static/src/scss/control_panel.scss',
            'web/static/src/scss/fields.scss',
            'web/static/src/scss/file_upload.scss',
            'web/static/src/scss/views.scss',
            'web/static/src/scss/pivot_view.scss',
            'web/static/src/scss/graph_view.scss',
            'web/static/src/scss/form_view.scss',
            'web/static/src/scss/list_view.scss',
            'web/static/src/scss/kanban_dashboard.scss',
            'web/static/src/scss/kanban_examples_dialog.scss',
            'web/static/src/scss/kanban_column_progressbar.scss',
            'web/static/src/scss/kanban_view.scss',
            'web/static/src/scss/web_calendar.scss',
            'web/static/src/scss/search_view.scss',
            'web/static/src/scss/search_panel.scss',
            'web/static/src/scss/dropdown_menu.scss',
            'web/static/src/scss/data_export.scss',
            'base/static/src/scss/onboarding.scss',
            'web/static/src/scss/attachment_preview.scss',
            'web/static/src/scss/notification.scss',
            'web/static/src/scss/base_document_layout.scss',
            'web/static/src/scss/special_fields.scss',
            'web/static/src/scss/ribbon.scss',
            'web/static/src/scss/base_settings.scss',
            'web/static/src/scss/report_backend.scss',

            ('include', 'web._backend_extra'),

            'base/static/src/js/res_config_settings.js',
            'web/static/lib/jquery.scrollTo/jquery.scrollTo.js',
            'web/static/lib/fuzzy-master/fuzzy.js',
            'web/static/lib/py.js/lib/py.js',
            'web/static/lib/py.js/lib/py_extras.js',
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',

            'web/static/src/js/_deprecated/*',
            'web/static/src/js/chrome/abstract_action.js',
            'web/static/src/js/chrome/abstract_web_client.js',
            'web/static/src/js/chrome/action_manager_act_window.js',
            'web/static/src/js/chrome/action_manager_report.js',
            'web/static/src/js/chrome/action_manager.js',
            'web/static/src/js/chrome/action_mixin.js',
            'web/static/src/js/chrome/apps_menu.js',
            'web/static/src/js/chrome/loading.js',
            'web/static/src/js/chrome/menu.js',
            'web/static/src/js/chrome/root_widget.js',
            'web/static/src/js/chrome/systray_menu.js',
            'web/static/src/js/chrome/user_menu.js',
            'web/static/src/js/chrome/web_client.js',
            'web/static/src/js/components/*',
            'web/static/src/js/control_panel/*',
            'web/static/src/js/core/domain.js',
            'web/static/src/js/core/mvc.js',
            'web/static/src/js/core/py_utils.js',
            'web/static/src/js/core/context.js',
            'web/static/src/js/core/data_comparison_utils.js',
            'web/static/src/js/core/math_utils.js',
            'web/static/src/js/core/misc.js',
            'web/static/src/js/fields/*',
            'web/static/src/js/report/utils.js',
            'web/static/src/js/report/client_action.js',
            'web/static/src/js/services/crash_manager_service.js',
            'web/static/src/js/services/data_manager.js',
            'web/static/src/js/services/report_service.js',
            'web/static/src/js/services/session.js',
            'web/static/src/js/tools/test_menus_loader.js',
            'web/static/src/js/tools/debug_manager_backend.js',
            'web/static/src/js/tools/tools.js',
            'web/static/src/js/views/abstract_view.js',
            'web/static/src/js/views/abstract_renderer.js',
            'web/static/src/js/views/abstract_renderer_owl.js',
            'web/static/src/js/views/abstract_model.js',
            'web/static/src/js/views/abstract_controller.js',
            'web/static/src/js/views/renderer_wrapper.js',
            'web/static/src/js/views/search_panel_model_extension.js',
            'web/static/src/js/views/search_panel.js',
            'web/static/src/js/views/action_model.js',
            'web/static/src/js/views/field_manager_mixin.js',
            'web/static/src/js/views/file_upload_mixin.js',
            'web/static/src/js/views/file_upload_progress_bar.js',
            'web/static/src/js/views/file_upload_progress_card.js',
            'web/static/src/js/views/sample_server.js',
            'web/static/src/js/views/select_create_controllers_registry.js',
            'web/static/src/js/views/signature_dialog.js',
            'web/static/src/js/views/standalone_field_manager_mixin.js',
            'web/static/src/js/views/view_registry.js',
            'web/static/src/js/views/view_dialogs.js',
            'web/static/src/js/views/view_utils.js',
            'web/static/src/js/views/basic/*',
            'web/static/src/js/views/calendar/*',
            'web/static/src/js/views/form/*',
            'web/static/src/js/views/graph/*',
            'web/static/src/js/views/kanban/*',
            'web/static/src/js/views/list/*',
            'web/static/src/js/views/pivot/*',
            'web/static/src/js/views/qweb/*',
            'web/static/src/js/widgets/change_password.js',
            'web/static/src/js/widgets/data_export.js',
            'web/static/src/js/widgets/date_picker.js',
            'web/static/src/js/widgets/domain_selector_dialog.js',
            'web/static/src/js/widgets/domain_selector.js',
            'web/static/src/js/widgets/iframe_widget.js',
            'web/static/src/js/widgets/model_field_selector.js',
            'web/static/src/js/widgets/switch_company_menu.js',
            'web/static/src/js/widgets/pie_chart.js',
            'web/static/src/js/widgets/ribbon.js',
            'web/static/src/js/widgets/signature.js',
            'web/static/src/js/widgets/attach_document.js',
            'web/static/src/js/apps.js',
            'web/static/src/js/env.js',
            'web/static/src/js/model.js',
            'web/static/src/js/owl_compatibility.js',
        ],
        'web.frontend_minimal_scripts': [
            'web/static/src/js/public/lazyloader.js',
        ],
        'web.frontend': [
            ('include', 'web._base_variables'),
            ('include', 'web._frontend_bootstrap_overrides'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._bootstrap'),

            'web/static/src/scss/base_frontend.scss',
            'web/static/src/scss/lazyloader.scss',
            'web/static/src/scss/navbar_mobile.scss',
            'web/static/src/scss/notification.scss',

            ('include', 'web.frontend_minimal_scripts'),

            'web/static/src/js/services/session.js',
            'web/static/src/js/public/public_env.js',
            'web/static/src/js/public/public_crash_manager.js',
            'web/static/src/js/public/public_notification.js',
            'web/static/src/js/public/public_root.js',
            'web/static/src/js/public/public_root_instance.js',
            'web/static/src/js/public/public_widget.js',
        ],
        'web.frontend_lazy': [
            ('include', 'web._base_variables'),
            ('include', 'web._frontend_bootstrap_overrides'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._bootstrap'),

            'web/static/src/scss/base_frontend.scss',
            'web/static/src/scss/lazyloader.scss',
            'web/static/src/scss/navbar_mobile.scss',
            'web/static/src/scss/notification.scss',

            'web/static/src/js/services/session.js',
            'web/static/src/js/public/public_env.js',
            'web/static/src/js/public/public_crash_manager.js',
            'web/static/src/js/public/public_notification.js',
            'web/static/src/js/public/public_root.js',
            'web/static/src/js/public/public_root_instance.js',
            'web/static/src/js/public/public_widget.js',
        ],
        'web.backend_prod_only': [
            'web/static/src/js/main.js',
        ],
        # Optional Bundle for PDFJS lib
        # Since PDFJS is quite huge (80000≈ lines), please only load it when it is necessary.
        # For now, it is only use to display the PDF slide Viewer during an embed.
        # Bundlized, the size is reduced to 5300≈ lines.
        'web.pdf_js_lib': [
            'web/static/lib/pdfjs/build/pdf.js',
            'web/static/lib/pdfjs/build/pdf.worker.js',
        ],
        'web.report_common': [
            ('include', 'web._base_variables'),

            'web/static/src/scss/bootstrap_overridden_report.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._bootstrap'),

            'base/static/src/css/description.css',
            'web/static/lib/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fonts.scss',
            'web/static/src/scss/report.scss',
            'web/static/src/scss/layout_standard.scss',
            'web/static/src/scss/layout_background.scss',
            'web/static/src/scss/layout_boxed.scss',
            'web/static/src/scss/layout_clean.scss',
            'web/static/src/scss/asset_styles_company_report.scss',

            'web/static/src/js/services/session.js',
            'web/static/src/js/public/public_root.js',
            'web/static/src/js/public/public_root_instance.js',
            'web/static/src/js/public/public_widget.js',
            'web/static/src/js/report/utils.js',
            'web/static/src/js/report/report.js',
        ],
        'web.report_pdf': [
            'web/static/src/css/reset.min.css',
        ],

        #----------------------------------------------------------------------
        # SUB BUNDLES
        #----------------------------------------------------------------------
        # These bundles can be used by main bundles but are not supposed to be
        # called directly from XML templates.
        #
        # Their naming conventions are similar to those of the main bundles,
        # with the addition of a prefixed underscore to reflect the "private"
        # aspect.
        #
        # Exemples:
        #   > web._helpers = define assets needed in most main bundles
        #
        # Note for backward compatibility:
        #   As for main bundles, the "assets_" prefix have been removed on all
        #   sub-bundles names.

        'web._primary_variables': [
            'web/static/src/scss/primary_variables.scss',
        ],
        'web._secondary_variables': [
            'web/static/src/scss/secondary_variables.scss',
        ],
        'web._base_variables': [
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_mixins.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/src/scss/utils.scss',

            ('include', 'web._primary_variables'),
            ('include', 'web._secondary_variables'),
        ],
        'web._bootstrap': [
            'web/static/src/scss/import_bootstrap.scss',
            'web/static/src/scss/bootstrap_review.scss',
        ],
        'web._backend_bootstrap_overrides': [
            'web/static/src/scss/bootstrap_overridden.scss',
        ],
        'web._backend_webclient': [
            'web/static/src/scss/webclient_extra.scss',
            'web/static/src/scss/webclient_layout.scss',
        ],
        'web._backend_extra': [
            'web/static/src/scss/dropdown_extra.scss',
            'web/static/src/scss/fields_extra.scss',
            'web/static/src/scss/form_view_extra.scss',
            'web/static/src/scss/list_view_extra.scss',
            'web/static/src/scss/search_view_extra.scss',
        ],
        'web._frontend_bootstrap_overrides': [
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
        ],
        'web._common_styles': [
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/lib/fontawesome/css/font-awesome.css',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/lib/tempusdominus/tempusdominus.scss',
            'web/static/src/scss/fonts.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/scss/ui_extra.scss',
            'web/static/src/scss/navbar.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/modal.scss',
            'web/static/src/scss/animation.scss',
            'web/static/src/scss/rainbow.scss',
            'web/static/src/scss/datepicker.scss',
            'web/static/src/scss/daterangepicker.scss',
            'web/static/src/scss/banner.scss',
            'web/static/src/scss/colorpicker.scss',
            'web/static/src/scss/popover.scss',
            'web/static/src/scss/translation_dialog.scss',
            'web/static/src/scss/keyboard.scss',
            'web/static/src/scss/name_and_signature.scss',
            'web/static/src/scss/web.zoomodoo.scss',
            'web/static/src/scss/color_picker.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
        ],
        'web._common_scripts': [
            'web/static/lib/underscore/underscore.js',
            'web/static/lib/underscore.string/lib/underscore.string.js',
            'web/static/lib/moment/moment.js',
            'web/static/lib/owl/owl.js',
            'web/static/src/js/component_extension.js',
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/jquery.ui/jquery-ui.js',
            'web/static/lib/jquery/jquery.browser.js',
            'web/static/lib/jquery.blockUI/jquery.blockUI.js',
            'web/static/lib/jquery.hotkeys/jquery.hotkeys.js',
            'web/static/lib/jquery.placeholder/jquery.placeholder.js',
            'web/static/lib/jquery.form/jquery.form.js',
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',
            'web/static/lib/jquery.mjs.nestedSortable/jquery.mjs.nestedSortable.js',
            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/index.js',
            'web/static/lib/bootstrap/js/util.js',
            'web/static/lib/bootstrap/js/alert.js',
            'web/static/lib/bootstrap/js/button.js',
            'web/static/lib/bootstrap/js/carousel.js',
            'web/static/lib/bootstrap/js/collapse.js',
            'web/static/lib/bootstrap/js/dropdown.js',
            'web/static/lib/bootstrap/js/modal.js',
            'web/static/lib/bootstrap/js/tooltip.js',
            'web/static/lib/bootstrap/js/popover.js',
            'web/static/lib/bootstrap/js/scrollspy.js',
            'web/static/lib/bootstrap/js/tab.js',
            'web/static/lib/bootstrap/js/toast.js',
            'web/static/lib/tempusdominus/tempusdominus.js',
            'web/static/lib/select2/select2.js',
            'web/static/lib/clipboard/clipboard.js',
            'web/static/lib/jSignature/jSignatureCustom.js',
            'web/static/lib/qweb/qweb2.js',
            'web/static/src/js/libs/autocomplete.js',
            'web/static/src/js/libs/bootstrap.js',
            'web/static/src/js/libs/content-disposition.js',
            'web/static/src/js/libs/download.js',
            'web/static/src/js/libs/fullcalendar.js',
            'web/static/src/js/libs/jquery.js',
            'web/static/src/js/libs/underscore.js',
            'web/static/src/js/libs/zoomodoo.js',
            'web/static/src/js/chrome/keyboard_navigation_mixin.js',
            'web/static/src/js/core/abstract_service.js',
            'web/static/src/js/core/abstract_storage_service.js',
            'web/static/src/js/core/ajax.js',
            'web/static/src/js/core/browser_detection.js',
            'web/static/src/js/core/bus.js',
            'web/static/src/js/core/custom_hooks.js',
            'web/static/src/js/core/class.js',
            'web/static/src/js/core/collections.js',
            'web/static/src/js/core/concurrency.js',
            'web/static/src/js/core/dialog.js',
            'web/static/src/js/core/owl_dialog.js',
            'web/static/src/js/core/popover.js',
            'web/static/src/js/core/dom.js',
            'web/static/src/js/core/local_storage.js',
            'web/static/src/js/core/mixins.js',
            'web/static/src/js/core/patch_mixin.js',
            'web/static/src/js/core/qweb.js',
            'web/static/src/js/core/ram_storage.js',
            'web/static/src/js/core/registry.js',
            'web/static/src/js/core/rpc.js',
            'web/static/src/js/core/service_mixins.js',
            'web/static/src/js/core/session.js',
            'web/static/src/js/core/session_storage.js',
            'web/static/src/js/core/time.js',
            'web/static/src/js/core/translation.js',
            'web/static/src/js/core/utils.js',
            'web/static/src/js/core/widget.js',
            'web/static/src/js/services/ajax_service.js',
            'web/static/src/js/services/config.js',
            'web/static/src/js/services/core.js',
            'web/static/src/js/services/local_storage_service.js',
            'web/static/src/js/services/notification_service.js',
            'web/static/src/js/services/crash_manager.js',
            'web/static/src/js/services/session_storage_service.js',
            'web/static/src/js/tools/debug_manager.js',
            'web/static/src/js/common_env.js',
            'web/static/src/js/widgets/name_and_signature.js',
            'web/static/src/js/widgets/notification.js',
            'web/static/src/js/widgets/rainbow_man.js',
            'web/static/src/js/core/smooth_scroll_on_drag.js',
            'web/static/src/js/widgets/colorpicker.js',
            'web/static/src/js/widgets/translation_dialog.js',
        ],

        # ----------------------------------------------------------------------
        # TESTS BUNDLES
        # ----------------------------------------------------------------------

        'web.test_tours': [
            # No tours are defined in web, but the bundle "web.test_tours" is
            # first called in web.
        ],
        'web.test_helpers': [
            'web/static/lib/daterangepicker/daterangepicker.css',
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/fullcalendar/core/main.css',
            'web/static/lib/fullcalendar/daygrid/main.css',
            'web/static/lib/fullcalendar/timegrid/main.css',
            'web/static/lib/fullcalendar/list/main.css',

            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/helpers/*.js',
            'web/static/lib/fullcalendar/core/main.js',
            'web/static/lib/fullcalendar/moment/main.js',
            'web/static/lib/fullcalendar/interaction/main.js',
            'web/static/lib/fullcalendar/daygrid/main.js',
            'web/static/lib/fullcalendar/timegrid/main.js',
            'web/static/lib/fullcalendar/list/main.js',
            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/javascript_highlight_rules.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-js.js',
            'web/static/lib/Chart/Chart.js',
            'web/static/lib/nearest/jquery.nearest.js',
            'web/static/lib/daterangepicker/daterangepicker.js',
            'web/static/src/js/libs/daterangepicker.js',
            'web/static/tests/main_tests.js',
        ],
        'web.qunit_suite_tests': [
            'base/static/tests/base_settings_tests.js',
            'web/static/tests/chrome/**/*.js',
            'web/static/tests/components/action_menus_tests.js',
            'web/static/tests/components/custom_checkbox_tests.js',
            'web/static/tests/components/custom_file_input_tests.js',
            'web/static/tests/components/datepicker_tests.js',
            'web/static/tests/components/dropdown_menu_tests.js',
            'web/static/tests/components/pager_tests.js',
            'web/static/tests/control_panel/**/*.js',
            'web/static/tests/core/**/*.js',
            'web/static/tests/fields/relational_fields/**/*.js',
            'web/static/tests/fields/basic_fields_tests.js',
            'web/static/tests/fields/field_utils_tests.js',
            'web/static/tests/fields/relational_fields_tests.js',
            'web/static/tests/fields/signature_tests.js',
            'web/static/tests/fields/special_fields_tests.js',
            'web/static/tests/fields/upgrade_fields_tests.js',
            'web/static/tests/services/**/*.js',
            'web/static/tests/tools/**/*.js',
            'web/static/tests/views/abstract_controller_tests.js',
            'web/static/tests/views/abstract_model_tests.js',
            'web/static/tests/views/abstract_view_banner_tests.js',
            'web/static/tests/views/abstract_view_tests.js',
            'web/static/tests/views/basic_model_tests.js',
            'web/static/tests/views/calendar_tests.js',
            'web/static/tests/views/form_tests.js',
            'web/static/tests/views/graph_tests.js',
            'web/static/tests/views/kanban_model_tests.js',
            'web/static/tests/views/kanban_tests.js',
            'web/static/tests/views/list_tests.js',
            'web/static/tests/views/pivot_tests.js',
            'web/static/tests/views/qweb_tests.js',
            'web/static/tests/views/sample_server_tests.js',
            'web/static/tests/views/search_panel_tests.js',
            'web/static/tests/views/view_dialogs_tests.js',
            'web/static/tests/widgets/**/*.js',
            'web/static/tests/component_extension_tests.js',
            'web/static/tests/mockserver_tests.js',
            'web/static/tests/owl_compatibility_tests.js',
            'web/static/tests/qweb_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js',
            'web/static/tests/fields/basic_fields_mobile_tests.js',
            'web/static/tests/fields/relational_fields_mobile_tests.js',
            'web/static/tests/components/dropdown_menu_mobile_tests.js',
        ],
        'web.benchmark_suite': [
            'web/static/lib/benchmarkjs/lodash.js',
            'web/static/lib/benchmarkjs/benchmark.js',
            'web/static/tests/views/form_benchmarks.js',
            'web/static/tests/views/kanban_benchmarks.js',
            'web/static/tests/views/list_benchmarks.js',
        ],

    },
    'bootstrap': True,  # load translations for login screen
}
