/** @odoo-module **/

/**
 * Module that contains registry for adding new models or patching models.
 * Useful for model manager in order to generate model classes.
 *
 * This code is not in model manager because other JS modules should populate
 * a registry, and it's difficult to ensure availability of the model manager
 * when these JS modules are deployed.
 */

const registry = {};
const featuresRegistry = {};

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * @private
 * @param {string} modelName
 * @returns {Object}
 */
function _getEntryFromModelName(modelName) {
    if (!registry[modelName]) {
        registry[modelName] = {
            dependencies: [],
            factory: undefined,
            name: modelName,
            patches: [],
        };
    }
    return registry[modelName];
}

/**
 * @private
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 * @param {Object} [param3={}]
 * @param {string} [param3.type='instance'] 'instance', 'class' or 'field'
 */
function _registerPatchModel(modelName, patchName, patch, { type = 'instance' } = {}) {
    const entry = _getEntryFromModelName(modelName);
    Object.assign(entry, {
        patches: (entry.patches || []).concat([{
            name: patchName,
            patch,
            type,
        }]),
    });
}

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * Register a patch for static methods in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerClassPatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'class' });
}

/**
 * Register a patch for fields in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerFieldPatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'field' });
}

/**
 * Register a patch for instance methods in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerInstancePatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'instance' });
}

/**
 * @param {string} name
 * @param {Object} definition
 * @param {Object} [definition.instanceMethods]
 * @param {Object} [definition.fields]
 */
function registerNewFeature(name, { instanceMethods = {}, fields = {} }) {
    if (featuresRegistry[name]) {
        throw new Error(`Feature "${name}" has already been registered!`);
    }
    if (registry[name]) {
        throw new Error(`Feature "${name}" is already the name of a model!`);
    }
    featuresRegistry[name] = {
        instanceMethods,
        fields,
    };
}

/**
 * @param {string} name
 * @param {function} factory
 * @param {string[]} [dependencies=[]]
 */
function registerNewModel(name, factory, dependencies = []) {
    if (featuresRegistry[name]) {
        throw new Error(`Model "${name}" is already the name of a feature!`);
    }
    const entry = _getEntryFromModelName(name);
    let entryDependencies = [...dependencies];
    if (name !== 'mail.model') {
        entryDependencies = [...new Set(entryDependencies.concat(['mail.model']))];
    }
    if (entry.factory) {
        throw new Error(`Model "${name}" has already been registered!`);
    }
    Object.assign(entry, {
        dependencies: entryDependencies,
        factory,
        name,
    });
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    featuresRegistry,
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
    registerNewFeature,
    registerNewModel,
    registry,
};

