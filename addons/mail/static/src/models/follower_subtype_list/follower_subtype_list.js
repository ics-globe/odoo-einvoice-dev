/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { many2one } from '@discuss/model/model_field';

function factory(dependencies) {

    class FollowerSubtypeList extends dependencies['discuss.model'] {}

    FollowerSubtypeList.fields = {
        follower: many2one('mail.follower'),
    };

    FollowerSubtypeList.modelName = 'mail.follower_subtype_list';

    return FollowerSubtypeList;
}

registerNewModel('mail.follower_subtype_list', factory);
