/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";

// -----------------------------------------------------------------------------
// startServices
// -----------------------------------------------------------------------------

export const SPECIAL_METHOD = Symbol("special_method");

/**
 * Start all services registered in the service registry, while making sure
 * each service dependencies are properly fulfilled.
 *
 * @param {OdooEnv} env
 * @returns {Promise<void>}
 */
export async function startServices(env) {
  const toStart = new Set();
  let timeoutId;
  serviceRegistry.on("UPDATE", null, async (payload) => {
    const { operation, key: name, value: service } = payload;
    if (operation === "delete") {
      // We hardly see why it would be usefull to remove a service.
      // Furthermore we could encounter problems with dependencies.
      // Keep it simple!
      return;
    }
    if (toStart.size) {
      const namedService = Object.assign(Object.create(service), { name });
      toStart.add(namedService);
    } else {
      timeoutId = await _startServices(env, toStart, timeoutId);
    }
  });
  timeoutId = await _startServices(env, toStart, timeoutId);
}

async function _startServices(env, toStart, timeoutId) {
  const services = env.services;
  for (const [name, service] of serviceRegistry.getEntries()) {
    if (!(name in services)) {
      const namedService = Object.assign(Object.create(service), { name });
      toStart.add(namedService);
    }
  }

  // start as many services in parallel as possible
  function start() {
    let service = null;
    const proms = [];
    while ((service = findNext())) {
      let name = service.name;
      toStart.delete(service);
      const value = service.start(env);
      if (value && "specializeForComponent" in service) {
        value[SPECIAL_METHOD] = service.specializeForComponent;
      }
      if (value instanceof Promise) {
        proms.push(
          value.then((val) => {
            services[name] = val || null;
            return start();
          })
        );
      } else {
        services[service.name] = value || null;
      }
    }
    return Promise.all(proms);
  }
  await start();
  clearTimeout(timeoutId);
  timeoutId = undefined;
  if (toStart.size) {
    const names = [...toStart].map((s) => s.name);
    timeoutId = setTimeout(() => {
      timeoutId = undefined;
      throw new Error(`Some services could not be started: ${names}`);
    }, 15000);
    toStart.clear();
  }
  return timeoutId;

  function findNext() {
    for (let s of toStart) {
      if (s.dependencies) {
        if (s.dependencies.every((d) => d in services)) {
          return s;
        }
      } else {
        return s;
      }
    }
    return null;
  }
}
