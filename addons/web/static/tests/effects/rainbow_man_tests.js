/** @odoo-module **/

import { Registry } from "@web/core/registry";
import { EffectContainer } from "@web/effects/effect_container";
import { effectService } from "@web/effects/effect_service";
import { RainbowMan } from "@web/effects/rainbow_man";
import { notificationService } from "@web/notifications/notification_service";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, getFixture, nextTick } from "../helpers/utils";

const { Component, mount, tags } = owl;

class Parent extends Component {
  setup() {
    this.RainbowMgr = EffectContainer;
  }
}
Parent.template = tags.xml`
    <div>
      <t t-component="RainbowMgr" />
    </div>
  `;

QUnit.module("RainbowMan", (hooks) => {
  let rainbowManDefault, serviceRegistry, target;
  hooks.beforeEach(async () => {
    rainbowManDefault = {
      message: "<div>Congrats!</div>",
      fadeout: "nextTick",
    };
    target = getFixture();
    serviceRegistry = new Registry();
    const user = makeFakeUserService({ showEffect: true });
    serviceRegistry.add("user", user);
    serviceRegistry.add("effect", effectService);
    serviceRegistry.add("notification", notificationService);
  });

  QUnit.test("rendering a rainbowman destroy after animation", async function (assert) {
    assert.expect(4);
    const _delays = RainbowMan.rainbowFadeouts;
    RainbowMan.rainbowFadeouts = { nextTick: 0 };
    const env = await makeTestEnv({ serviceRegistry });
    const parent = await mount(Parent, { env, target });
    env.services.effect.create(rainbowManDefault.message, rainbowManDefault);
    await nextTick();
    assert.containsOnce(target, ".o_reward");
    assert.containsOnce(parent.el, ".o_reward_rainbow");
    assert.strictEqual(
      parent.el.querySelector(".o_reward_msg_content").innerHTML,
      "<div>Congrats!</div>"
    );

    const ev = new AnimationEvent("animationend", { animationName: "reward-fading-reverse" });
    target.querySelector(".o_reward").dispatchEvent(ev);
    await nextTick();
    assert.containsNone(target, ".o_reward");
    RainbowMan.rainbowFadeouts = _delays;
    parent.destroy();
  });

  QUnit.test("rendering a rainbowman destroy on click", async function (assert) {
    assert.expect(3);
    rainbowManDefault.fadeout = "no";
    const env = await makeTestEnv({ serviceRegistry });
    const parent = await mount(Parent, { env, target });
    env.services.effect.create(rainbowManDefault.message, rainbowManDefault);
    await nextTick();
    assert.containsOnce(parent.el, ".o_reward");
    assert.containsOnce(parent.el, ".o_reward_rainbow");
    await click(target);
    assert.containsNone(target, ".o_reward");
    parent.destroy();
  });
});
