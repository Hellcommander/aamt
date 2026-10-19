#pragma once

#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>
#include <optional>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <tuple>
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

namespace MagiTech::GeneratorAgent {

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
  std::vector<std::string>        tags;
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
  explicit LuaSpell(sol::table t)
    : tbl_(t),
      fnInit_(t.get<sol::function>("init")),
      fnCast_(t.get<sol::function>("cast"))
  {
    if (!fnCast_.valid() || fnCast_.get_type() != sol::type::function)
      throw std::runtime_error("LuaSpell: missing 'cast'");
  }

  void init(const SpellDefinition& def) override {
    if (fnInit_.valid() && fnInit_.get_type() == sol::type::function)
      SafeCall::call(fnInit_, "LuaSpell::init", tbl_, def.id, def.params);
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

// Copies share the underlying spell object (caches hand out copies of one instance).
class SpellInstance {
public:
  SpellInstance(std::unique_ptr<ISpell> s, SpellDefinition const& def)
    : spell_(std::move(s)), def_(def)
  {
    if (!spell_) throw std::invalid_argument("SpellInstance: null spell for '" + def_.id + "'");
    HybridBusPluginRegistry::instance()
      .dispatch(SpellRegisteredEvent{def_.id});
    spell_->init(def_);
  }

  void cast(int casterId, nlohmann::json const& args) {
    HybridBusPluginRegistry::instance()
      .dispatch(SpellCastEvent{def_.id, casterId, args});
    spell_->cast(casterId, args);
  }

  const SpellDefinition& definition() const { return def_; }
  const std::string& id() const { return def_.id; }

private:
  std::shared_ptr<ISpell> spell_;
  SpellDefinition         def_;
};

//---------------------------------------------------------------------------
// SpellGenerator (factory; a process-wide instance is available via instance())

class SpellGenerator {
public:
  using ManifestErrors = std::vector<BlazeJsonHelper::JsonErrorInfo>;

  static SpellGenerator& instance() {
    static SpellGenerator G;
    return G;
  }

  SpellGenerator() { evt::Bus::ensureInitialized(); }
  ~SpellGenerator() { stopWatching(); }

  SpellGenerator(const SpellGenerator&) = delete;
  SpellGenerator& operator=(const SpellGenerator&) = delete;

  // Load or reload the manifest, returning syntax+semantic errors
  auto loadManifest(std::filesystem::path const& path)
    -> std::expected<void, ManifestErrors>
  {
    // Use the enhanced Blaze JSON helper
    auto result = BlazeJsonHelper::loadFileEnhanced(path);
    if (!result.success) {
      return std::unexpected(result.errors);
    }

    nlohmann::json j = result.data;
    ManifestErrors sem;
    DefinitionMap defs{&pool_};

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

      std::string key = def.id;
      defs.emplace(std::move(key), std::move(def));
    }

    if (!sem.empty()) return std::unexpected(std::move(sem));

    {
      std::unique_lock lk(mtx_);
      manifestPath_ = path;
      definitions_.swap(defs);   // both maps allocate from pool_
    }

    return {};
  }

  std::filesystem::path manifestPath() const {
    std::shared_lock lk(mtx_);
    return manifestPath_;
  }

  bool hasDefinition(std::string const& id) const {
    std::shared_lock lk(mtx_);
    return definitions_.find(id) != definitions_.end();
  }

  std::vector<std::string> definitionIds() const {
    std::shared_lock lk(mtx_);
    std::vector<std::string> ids;
    ids.reserve(definitions_.size());
    for (auto const& [id, def] : definitions_) ids.push_back(id);
    return ids;
  }

  std::optional<SpellDefinition> findDefinition(std::string const& id) const {
    std::shared_lock lk(mtx_);
    if (auto it = definitions_.find(id); it != definitions_.end()) return it->second;
    return std::nullopt;
  }

  std::vector<SpellDefinition> definitions() const {
    std::shared_lock lk(mtx_);
    std::vector<SpellDefinition> out;
    out.reserve(definitions_.size());
    for (auto const& [id, def] : definitions_) out.push_back(def);
    return out;
  }

  /// Adds or replaces a definition (e.g. imported or synthesized at runtime).
  void upsertDefinition(SpellDefinition def) {
    std::unique_lock lk(mtx_);
    std::string key = def.id;
    definitions_.insert_or_assign(std::move(key), std::move(def));
  }

  /// Applies `edit` to the stored definition; returns false when the id is unknown.
  bool updateDefinition(std::string const& id, std::function<void(SpellDefinition&)> const& edit) {
    std::unique_lock lk(mtx_);
    auto it = definitions_.find(id);
    if (it == definitions_.end()) return false;
    edit(it->second);
    return true;
  }

  bool isManifestLoaded() const {
    std::shared_lock lk(mtx_);
    return !manifestPath_.empty();
  }

  /// True when some registered C++/Lua factory (exact or pattern) handles `type`.
  bool hasFactoryFor(std::string const& type) const {
    std::shared_lock lk(mtx_);
    if (cppFac_.count(type) || luaFac_.count(type)) return true;
    for (auto const& [pat, fac] : patternFac_)
      if (EventPatternMatcher::matches(pat, type)) return true;
    for (auto const& [pat, fac] : luaPatterns_)
      if (EventPatternMatcher::matches(pat, type)) return true;
    return false;
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
    return createFromDefinition(def);
  }

  // Create a spell instance from an explicit definition (not necessarily in the manifest)
  auto createFromDefinition(SpellDefinition const& def)
    -> std::expected<SpellInstance, std::string>
  {
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
    stopWatching();
    quit_ = false;
    watcher_ = std::thread([this,interval]{
      std::error_code ec;
      const auto path = manifestPath();
      auto last = std::filesystem::last_write_time(path, ec);
      while (!quit_) {
        std::this_thread::sleep_for(interval);
        auto now = std::filesystem::last_write_time(path, ec);
        if (ec) continue;   // file temporarily missing (e.g. being rewritten)
        if (now != last) {
          last = now;
          auto r = loadManifest(path);
          if (!r) {
            for (auto const& err : r.error())
              std::cerr << "[SpellGen] reload: " << err.message << "\n";
          }
        }
      }
    });
  }

  void stopWatching() noexcept {
    quit_ = true;
    if (watcher_.joinable()) watcher_.join();
  }

  bool isWatching() const noexcept { return watcher_.joinable() && !quit_; }

  // Bind to Lua
  void bind(sol::state& lua) {
    lua.new_usertype<SpellInstance>("SpellInstance",
      sol::no_constructor,
      "cast", &SpellInstance::cast);

    lua.new_usertype<BlazeJsonHelper::JsonErrorInfo>("JsonErrorInfo",
      sol::no_constructor,
      "line", &BlazeJsonHelper::JsonErrorInfo::line,
      "column", &BlazeJsonHelper::JsonErrorInfo::column,
      "code", &BlazeJsonHelper::JsonErrorInfo::code,
      "message", &BlazeJsonHelper::JsonErrorInfo::message);

    sol::table S = lua.create_named_table("Spell");
    S.set_function("loadManifest", [this](std::string p) -> std::tuple<bool, ManifestErrors> {
      auto res = loadManifest(p);
      if (!res) return {false, res.error()};
      return {true, ManifestErrors{}};
    });
    S.set_function("registerType",
      [this](std::string t, sol::function f){ registerLuaFactory(t,f); });
    S.set_function("registerPattern",
      [this](std::string pat, sol::function f){ registerLuaPattern(pat,f); });
    S.set_function("create",
      [this](std::string id){
        auto r = create(id);
        if (!r) throw std::runtime_error(r.error());
        return std::move(*r);
      });
    S.set_function("watch", [this](sol::optional<double> seconds){
      watchManifest(std::chrono::milliseconds(static_cast<int>(seconds.value_or(1.0) * 1000)));
    });
    S.set_function("stopWatch", [this](){ stopWatching(); });
  }

private:
  using DefinitionMap = std::pmr::unordered_map<std::string, SpellDefinition>;

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
    if (auto it=luaFac_.find(d.type); it!=luaFac_.end())
      return makeLuaSpell(SafeCall::call(it->second, "LuaFactory:"+d.type, d.id, d.params));
    return std::nullopt;
  }
  std::optional<std::unique_ptr<ISpell>> tryLuaPattern(SpellDefinition const& d) {
    std::shared_lock lk(mtx_);
    for (auto& [pat,fac] : luaPatterns_)
      if (EventPatternMatcher::matches(pat, d.type))
        return makeLuaSpell(SafeCall::call(fac, "LuaPattern:"+pat, d.id, d.params));
    return std::nullopt;
  }
  // A Lua factory must return a table with a 'cast' function; anything else means "no spell".
  static std::optional<std::unique_ptr<ISpell>> makeLuaSpell(sol::object const& obj) {
    if (!obj.valid() || obj.get_type() != sol::type::table) return std::nullopt;
    return std::make_unique<LuaSpell>(obj.as<sol::table>());
  }

  // Data members (pool_ first: the pmr maps below allocate from it)
  std::pmr::synchronized_pool_resource pool_;
  std::filesystem::path     manifestPath_;
  DefinitionMap definitions_{&pool_};
  std::unordered_map<std::string,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)>> cppFac_;
  std::pmr::unordered_map<std::string, sol::function> luaFac_{&pool_};
  std::vector<std::pair<std::string,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)>>> patternFac_;
  std::vector<std::pair<std::string, sol::function>> luaPatterns_;
  mutable std::shared_mutex  mtx_;
  std::thread                watcher_;
  std::atomic<bool>          quit_{false};
};

} // namespace MagiTech::GeneratorAgent
