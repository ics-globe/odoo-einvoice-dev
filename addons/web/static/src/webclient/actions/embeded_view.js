/** @odoo-module */

const { Component, xml } = owl;

export class EmbededView extends Component {}
EmbededView.template = xml`
    <div class="o_embeded_view">
        <t t-if="props.ActionComponent" t-component="props.ActionComponent" t-props="props.actionProps"/>
    </div>
`;
EmbededView.props = {
    ActionComponent: { optional: true },
    actionProps: { optional: true },
};

export default EmbededView;
