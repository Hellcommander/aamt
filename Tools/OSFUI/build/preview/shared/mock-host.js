// Mock OSF UI host for browser preview. Never shipped into Data.
(function () {
  const VALUES = {
  "General.EnableWeaponStarbornCasting": false,
  "General.ReplaceNormalFire": false,
  "General.RequireArcaneConduit": true,
  "General.DrainEssence": true,
  "General.DefaultEssenceCost": 0,
  "Hooks.ShipWeaponFireSignature": "",
  "Hooks.UseWeaponFiredEventFallback": true,
  "Hooks.FireHookProbe": 0,
  "Hooks.FireHookID": 105260,
  "Requirements.RequireStarbornPilot": true,
  "Requirements.StarbornKeywordEditorID": "",
  "Requirements.RequireSeatAbility": true,
  "Requirements.SeatAbilityEditorID": "ABL_StarbornWeaponInterface",
  "Requirements.SeatActiveKeywordEditorID": "KW_ShipWeaponPilotActive",
  "Requirements.MinStarPowerPercent": 0,
  "Requirements.DefaultStarPowerCost": 25,
  "Scaling.BaseDamage": 100,
  "Scaling.BaseRadius": 50,
  "Scaling.BaseDuration": 5,
  "Scaling.PilotLevelDamageScale": 2.0,
  "Scaling.GunnerSkillDamageScale": 1.5,
  "Scaling.PilotStarbornRankRadiusScale": 3.0,
  "Scaling.GunnerPerkDurationScale": 1.2,
  "Chance.BaseChancePercent": 100,
  "Chance.DefaultCooldownSeconds": 5,
  "Chance.LowHullBonusChance": 20,
  "Stats.GunnerSkillEditorID": "",
  "Stats.GunnerBonusPerkID": 0,
  "PerkIntegration.Enabled": true,
  "PerkIntegration.ExcludeSummonPowers": 1,
  "PerkIntegration.StarbornKeywordFilter": "Starborn"
};
  const SAMPLES = {};
  const MOD = "arendeth.ship-weapon-powers";

  window.osfui = window.osfui || {};
  window.osfui.postMessage = function (json) {
    const message = JSON.parse(json);
    const payload = message.payload || {};
    if (payload.command === "settings.get") {
      reply(message.requestId, "settings.data", { mod: MOD, values: VALUES });
    } else if (payload.command === "settings.set") {
      VALUES[payload.key] = payload.value;
      reply(message.requestId, "ui.result", { ok: true, command: "settings.set" });
      deliver("settings.changed", { mod: MOD, key: payload.key, value: payload.value });
    } else if (payload.command === "ui.action") {
      console.log("[mock] action", payload.action, payload.args || []);
      reply(message.requestId, "ui.result", { ok: true, command: "ui.action" });
    } else if (payload.command === "i18n.get") {
      reply(message.requestId, "i18n.data", { locale: "en", strings: {} });
    } else {
      reply(message.requestId, "ui.result", { ok: true, command: payload.command });
    }
  };

  function send(message) { window.osfui.onMessage(JSON.stringify(message)); }
  function reply(requestId, type, payload) { setTimeout(() => send({ type, requestId, payload }), 10); }
  function deliver(type, payload) { setTimeout(() => send({ type, payload }), 10); }

  window.addEventListener("DOMContentLoaded", () => {
    send({ type: "runtime.ready", payload: { version: "1.5.0-preview" } });
    for (const [key, value] of Object.entries(SAMPLES)) {
      deliver("data.state", { mod: MOD, key, value });
    }
  });
})();
