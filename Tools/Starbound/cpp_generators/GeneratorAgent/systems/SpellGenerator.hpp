#pragma once

#include <filesystem>
#include <fstream>
#include <shared_mutex>
#include <thread>
#include <chrono>
#include <atomic>
#include <expected>
#include <unordered_map>
#include <vector>
#include <memory_resource>
#include "vendor/json/include/nlohmann/json.hpp"
#include <sol/sol.hpp>
#include "core/utils/BlazeJsonHelper.hpp"
#include "core/utils/JsonHelper.hpp"
#include "core/plugins/HybridBusPluginRegistry.hpp"
#include "core/utils/SafeCall.hpp"
#include "core/utils/EventPatternMatcher.hpp"
#include "core/threading/UnifiedThreadingSystem.hpp"
#include "IMagiTechModule.hpp"

//---------------------------------------------------------------------------
// Spell Events

struct SpellRegisteredEvent {
  std::string spellId;
};

struct SpellCastEvent {
  std::string spellId;
  int         casterId;
  nlohmann::json args;
};

//---------------------------------------------------------------------------
// SpellDefinition

struct SpellDefinition {
  std::string                     id;
  std::string                     type;
  nlohmann::json                  params;
  std::string                     displayName;
  std::string                     description;
  std::pmr::vector<std::string>   tags;
};

//---------------------------------------------------------------------------
// ISpell (Interface)

class ISpell {
public:
  virtual ~ISpell() = default;
  virtual void init(const SpellDefinition& def) {}
  virtual void cast(int casterId, const nlohmann::json& args) = 0;
};

//---------------------------------------------------------------------------
// LuaSpell (wraps a Lua table into ISpell)

class LuaSpell : public ISpell {
public:
  LuaSpell(sol::table t)
    : tbl_(t),
      fnInit_(t["init"]),
      fnCast_(t["cast"])
  {
    if (!fnCast_) throw std::runtime_error("LuaSpell: missing 'cast'");
  }

  void init(const SpellDefinition& def) override {
    if (fnInit_) SafeCall::call(fnInit_, "LuaSpell::init", tbl_, def.id, def.params);
  }

  void cast(int casterId, const nlohmann::json& args) override {
    SafeCall::call(fnCast_, "LuaSpell::cast", tbl_, casterId, args);
  }

private:
  sol::table    tbl_;
  sol::function fnInit_;
  sol::function fnCast_;
};

//---------------------------------------------------------------------------
// SpellInstance (wrap ISpell + publish events)

class SpellInstance {
public:
  SpellInstance(std::unique_ptr<ISpell> s, SpellDefinition const& def)
    : spell_(std::move(s)), def_(def)
  {
    HybridBusPluginRegistry::instance()
      .dispatch(SpellRegisteredEvent{def_.id});
    spell_->init(def_);
  }

  void cast(int casterId, nlohmann::json const& args) {
    HybridBusPluginRegistry::instance()
      .dispatch(SpellCastEvent{def_.id, casterId, args});
    spell_->cast(casterId, args);
  }

private:
  std::unique_ptr<ISpell> spell_;
  SpellDefinition         def_;
};

//---------------------------------------------------------------------------
// SpellGenerator (singleton factory)

class SpellGenerator {
public:
  static SpellGenerator& instance() {
    static SpellGenerator G;
    return G;
  }

  // Load or reload the manifest, returning syntax+semantic errors
  auto loadManifest(std::filesystem::path const& path)
    -> std::expected<void, std::vector<BlazeJsonHelper::JsonErrorInfo>>
  {
    // Use the enhanced Blaze JSON helper
    auto result = BlazeJsonHelper::loadFileEnhanced(path);
    if (!result.success) {
      return std::unexpected(result.errors);
    }

    nlohmann::json j = result.data;
    std::vector<BlazeJsonHelper::JsonErrorInfo> sem;
    pmr::unordered_map<std::string,SpellDefinition> defs{&pool_};

    for (auto& sj : j.value("spells", nlohmann::json::array())) {
      SpellDefinition def;
      auto e1 = JsonHelper::expectKey(sj,"id",def.id);
      auto e2 = JsonHelper::expectKey(sj,"type",def.type);
      if (!e1.success) sem.push_back(BlazeJsonHelper::JsonErrorInfo{0,0,"MissingField",e1.message});
      if (!e2.success) sem.push_back(BlazeJsonHelper::JsonErrorInfo{0,0,"MissingField",e2.message});
      def.params      = JsonHelper::getObject(sj, "params", {});
      def.displayName = JsonHelper::getString(sj, "displayName", def.id);
      def.description = JsonHelper::getString(sj, "description", "");
      
      auto tags = JsonHelper::getArray(sj, "tags", nlohmann::json::array());
      for (auto& t : tags) {
        if (t.is_string()) {
          def.tags.push_back(t.get<std::string>());
        }
      }

      defs.emplace(def.id, std::move(def));
    }

    if (!sem.empty()) return std::unexpected(sem);

    {
      std::unique_lock lk(mtx_);
      manifestPath_ = path;
      definitions_.swap(defs);
    }

    return {};
  }

  // Register factories
  void registerCppFactory(std::string_view type,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> fac)
  {
    std::unique_lock lk(mtx_);
    cppFac_[std::string(type)] = std::move(fac);
  }

  void registerLuaFactory(std::string_view type, sol::function fac) {
    std::unique_lock lk(mtx_);
    luaFac_[std::string(type)] = std::move(fac);
  }

  void registerPatternFactory(std::string pattern,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> fac)
  {
    std::unique_lock lk(mtx_);
    patternFac_.emplace_back(std::move(pattern), std::move(fac));
  }

  void registerLuaPattern(std::string pattern, sol::function fac) {
    std::unique_lock lk(mtx_);
    luaPatterns_.emplace_back(std::move(pattern), std::move(fac));
  }

  // Create a spell instance or error
  auto create(std::string const& id)
    -> std::expected<SpellInstance, std::string>
  {
    SpellDefinition def;
    {
      std::shared_lock lk(mtx_);
      if (auto it = definitions_.find(id); it!=definitions_.end())
        def = it->second;
      else return std::unexpected("Unknown spell '" + id + "'");
    }

    // 1) C++ exact
    if (auto s = tryCpp(def)) return SpellInstance(std::move(*s), def);
    // 2) C++ pattern
    if (auto s = tryPattern(def)) return SpellInstance(std::move(*s), def);
    // 3) Lua exact
    if (auto s = tryLua(def)) return SpellInstance(std::move(*s), def);
    // 4) Lua pattern
    if (auto s = tryLuaPattern(def)) return SpellInstance(std::move(*s), def);

    return std::unexpected("No factory for type '" + def.type + "'");
  }

  // Hot-reload watcher
  void watchManifest(std::chrono::milliseconds interval = std::chrono::seconds(1)) {
    watcher_ = std::thread([this,interval]{
      auto last = std::filesystem::last_write_time(manifestPath_);
      while (!quit_) {
        std::this_thread::sleep_for(interval);
        auto now = std::filesystem::last_write_time(manifestPath_);
        if (now != last) {
          last = now;
          auto r = loadManifest(manifestPath_);
          if (!r) {
            for (auto& err : *r.error())
              std::cerr << "[SpellGen] reload: " << err.msg << "\n";
          }
        }
      }
    });
  }

  void stopWatching() noexcept {
    quit_ = true;
    if (watcher_.joinable()) watcher_.join();
  }

  // Bind to Lua
  void bind(sol::state& lua) {
    lua.new_usertype<SpellInstance>("SpellInstance",
      "cast", &SpellInstance::cast);

    sol::table S = lua.create_named_table("Spell");
    S.set_function("loadManifest", [&](std::string p){
      auto res = loadManifest(p);
      if (!res) return std::make_tuple(false, *res.error());
      return std::make_tuple(true, std::vector<BlazeJsonHelper::JsonErrorInfo>{});
    });
    S.set_function("registerType",
      [&](std::string t, sol::function f){ registerLuaFactory(t,f); });
    S.set_function("registerPattern",
      [&](std::string pat, sol::function f){ registerLuaPattern(pat,f); });
    S.set_function("create",
      [&](std::string id){
        auto r = create(id);
        if (!r) throw std::runtime_error(r.error());
        return *r;
      });
    S.set_function("watch", [&](sol::optional<double> ms){
      watchManifest(std::chrono::milliseconds(int(ms.value_or(1.0)*1000)));
    });
    S.set_function("stopWatch", [&](){ stopWatching(); });
  }

private:
  SpellGenerator() { evt::Bus::ensureInitialized(); }
  ~SpellGenerator() { stopWatching(); }

  std::optional<std::unique_ptr<ISpell>> tryCpp(SpellDefinition const& d) {
    std::shared_lock lk(mtx_);
    if (auto it=cppFac_.find(d.type); it!=cppFac_.end())
      return it->second(d);
    return std::nullopt;
  }
  std::optional<std::unique_ptr<ISpell>> tryPattern(SpellDefinition const& d) {
    std::shared_lock lk(mtx_);
    for (auto& [pat,fac] : patternFac_)
      if (EventPatternMatcher::matches(pat, d.type))
        return fac(d);
    return std::nullopt;
  }
  std::optional<std::unique_ptr<ISpell>> tryLua(SpellDefinition const& d) {
    std::shared_lock lk(mtx_);
    if (auto it=luaFac_.find(d.type); it!=luaFac_.end()) {
      auto obj = SafeCall::call(it->second, "LuaFactory:"+d.type, d.id, d.params);
      auto tbl = obj.as<sol::table>();
      return std::make_unique<LuaSpell>(tbl);
    }
    return std::nullopt;
  }
  std::optional<std::unique_ptr<ISpell>> tryLuaPattern(SpellDefinition const& d) {
    std::shared_lock lk(mtx_);
    for (auto& [pat,fac] : luaPatterns_)
      if (EventPatternMatcher::matches(pat, d.type)) {
        auto obj = SafeCall::call(fac, "LuaPattern:"+pat, d.id, d.params);
        auto tbl = obj.as<sol::table>();
        return std::make_unique<LuaSpell>(tbl);
      }
    return std::nullopt;
  }

  // Data members
  std::filesystem::path     manifestPath_;
  pmr::unordered_map<std::string,SpellDefinition> definitions_{&pool_};
  std::unordered_map<std::string,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)>> cppFac_;
  pmr::unordered_map<std::string, sol::function> luaFac_{&pool_};
  std::vector<std::pair<std::string,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)>>> patternFac_;
  std::vector<std::pair<std::string, sol::function>> luaPatterns_;
  std::shared_mutex          mtx_;
  pmr::unsynchronized_pool_resource pool_;
  std::thread                watcher_;
  std::atomic<bool>          quit_{false};
}; 

} // namespace MagiTech::GeneratorAgent


