odoo.define('hr_expense.expenses.tree', function (require) {
"use strict";
    var DocumentUploadMixin = require('hr_expense.documents.upload.mixin');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var KanbanRenderer = require('web.KanbanRenderer');
    var session = require('web.session');
    const config = require('web.config');

    var QWeb = core.qweb;

    var ExpensesListController = ListController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
        /**
         * @override
         */
         init: function () {
            this._super.apply(this, arguments);
            this.isMobile = config.device.isMobileDevice;
        },

        _onSelectionChanged: function (ev) {
            this._super.apply(this, arguments);
            const records = this.getSelectedRecords();
            const displaySubmit = records.length?records.every(record => record.data.state === 'draft') : false;
            const displayApprove = records.length?records.every(record => record.data.state === 'submit') : false;
            const displayPost = records.length?records.every(record => record.data.state === 'approve') : false;
            const displayRegister = records.length?records.every(record => record.data.state === 'post') : false;

            if (displaySubmit) {
                this.$buttons.find('.o_button_submit_sheet').removeClass('d-none');
            } else {
            this.$buttons.find('.o_button_submit_sheet').addClass('d-none');
            }

            if (displayApprove) {
                this.$buttons.find('.o_button_approve_sheet').removeClass('d-none');
            } else {
            this.$buttons.find('.o_button_approve_sheet').addClass('d-none');
            }

            if (displayPost) {
                this.$buttons.find('.o_button_post_sheet').removeClass('d-none');
            } else {
            this.$buttons.find('.o_button_post_sheet').addClass('d-none');
            }

            if (displayRegister) {
                this.$buttons.find('.o_button_register_payment').removeClass('d-none');
            } else {
            this.$buttons.find('.o_button_register_payment').addClass('d-none');
            }
        },

        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.on('click', '.o_button_create_report', this._onCreateReportClick.bind(this));
        },

        /**
         * Create Report from the selected expense records
         * @param {*} ev
         */
         _onCreateReportClick: function(ev) {
            let records = this.getSelectedRecords();
            // to get all the records that are showing

            const state = this.model.get(this.handle, {raw: true});
            let record_ids = records.map(record => record.res_id);
            this._rpc({
                model: 'hr.expense',
                method: 'get_expenses_to_submit',
                args: [record_ids],
                context: this.context,
            });

        },
    });

    const ExpenseQRCodeMixin = {
        async _renderView() {
            const self = this;
            await this._super(...arguments);
            const google_url = "https://play.google.com/store/apps/details?id=com.odoo.mobile";
            const apple_url = "https://apps.apple.com/be/app/odoo/id1272543640";
            const action_desktop = {
                name: 'Download our App',
                type: 'ir.actions.client',
                tag: 'expense_qr_code_modal',
                params: {'url': "https://apps.apple.com/be/app/odoo/id1272543640"},
                target: 'new',
            };
            this.$el.find('img.o_expense_apple_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobileDevice) {
                    self.do_action(_.extend(action_desktop, {params: {'url': apple_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: apple_url});
                }
            });
            this.$el.find('img.o_expense_google_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobileDevice) {
                    self.do_action(_.extend(action_desktop, {params: {'url': google_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: google_url});
                }
            });
        },
    };

    const ExpenseDashboardMixin = {
        _render: async function () {
            var self = this;
            await this._super(...arguments);
            const result = await this._rpc({
                model: 'hr.expense',
                method: 'get_expense_dashboard',
                context: this.context,
            });

            self.$el.parent().find('.o_expense_container').remove();
            const elem = QWeb.render('hr_expense.dashboard_list_header', {
                expenses: result,
                render_monetary_field: self.render_monetary_field,
            });
            self.$el.before(elem);
        },
        render_monetary_field: function (value, currency_id) {
            value = value.toFixed(2);
            var currency = session.get_currency(currency_id);
            if (currency) {
                if (currency.position === "after") {
                    value += currency.symbol;
                } else {
                    value = currency.symbol + value;
                }
            }
            return value;
        }
    };

    // Expense List Renderer
    var ExpenseListRenderer = ListRenderer.extend(ExpenseQRCodeMixin);

    // Expense List Renderer with the Header
    // Used in "My Expenses to Report", "All My Expenses" & "My Reports"
    var ExpenseListRendererHeader = ExpenseListRenderer.extend(ExpenseDashboardMixin);

    var ExpensesListViewDashboardUpload = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ExpenseListRenderer,
            Controller: ExpensesListController,
        }),
    });

    // Used in "My Expenses to Report" & "All My Expenses"
    var ExpensesListViewDashboardUploadHeader = ExpensesListViewDashboardUpload.extend({
        config: _.extend({}, ExpensesListViewDashboardUpload.prototype.config, {
            Renderer: ExpenseListRendererHeader,
        }),
    });

    // The dashboard view of the expense module
    var ExpensesListViewDashboard = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ExpenseListRenderer,
            Controller: ExpensesListController,
        }),
    });

    // The dashboard view of the expense module with an header
    // Used in "My Expenses"
    var ExpensesListViewDashboardHeader = ExpensesListViewDashboard.extend({
        config: _.extend({}, ExpensesListViewDashboard.prototype.config, {
            Renderer: ExpenseListRendererHeader,
        })
    });

    var ExpensesKanbanController = KanbanController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesKanbanView.buttons',
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var ExpenseKanbanRenderer = KanbanRenderer.extend(ExpenseQRCodeMixin);

    var ExpenseKanbanRendererHeader = ExpenseKanbanRenderer.extend(ExpenseDashboardMixin);

    // The kanban view
    var ExpensesKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ExpensesKanbanController,
            Renderer: ExpenseKanbanRenderer,
        }),
    });

    // The kanban view with the Header
    // Used in "My Expenses to Report", "All My Expenses" & "My Repo
    var ExpensesKanbanViewHeader = ExpensesKanbanView.extend({
        config: _.extend({}, ExpensesKanbanView.prototype.config, {
            Renderer: ExpenseKanbanRendererHeader,
        })
    });

    viewRegistry.add('hr_expense_tree_dashboard_upload', ExpensesListViewDashboardUpload);
    // Tree view with the header.
    // Used in "My Expenses to Report" & "All My Expenses"
    viewRegistry.add('hr_expense_tree_dashboard_upload_header', ExpensesListViewDashboardUploadHeader);
    viewRegistry.add('hr_expense_tree_dashboard', ExpensesListViewDashboard);
    // Tree view with the header.
    // Used in "My Reports"
    viewRegistry.add('hr_expense_tree_dashboard_header', ExpensesListViewDashboardHeader);
    viewRegistry.add('hr_expense_kanban', ExpensesKanbanView);
    // Kanban view with the header.
    // Used in "My Expenses to Report", "All My Expenses" & "My Reports"
    viewRegistry.add('hr_expense_kanban_header', ExpensesKanbanViewHeader);
});
