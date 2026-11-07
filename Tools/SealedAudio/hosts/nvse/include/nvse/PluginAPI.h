#pragma once
// The parts of the NVSE / xNVSE plugin API this host uses, written down from the published PluginAPI.h of the New Vegas
// Script Extender (unchanged in shape since 1.x). 32-bit only. Only the fields read here matter: nvseVersion,
// runtimeVersion, isEditor, QueryInterface and GetPluginHandle come first in NVSEInterface, and the messaging interface
// is interface id 2 with RegisterListener(handle, sender, callback).

#include <cstdint>

typedef std::uint32_t UInt32;
typedef std::uint32_t PluginHandle;

enum
{
	kPluginHandle_Invalid = 0xFFFFFFFF
};

struct PluginInfo
{
	enum
	{
		kInfoVersion = 1
	};
	UInt32      infoVersion;
	const char* name;
	UInt32      version;
};

enum
{
	kInterface_Serialization = 0,
	kInterface_Console,
	kInterface_Messaging,
	kInterface_CommandTable,
	kInterface_StringVar,
	kInterface_ArrayVar,
	kInterface_Script,
	kInterface_Data,
	kInterface_EventManager,
	kInterface_LoggingInterface,
	kInterface_Max
};

struct CommandInfo;

struct NVSEInterface
{
	UInt32 nvseVersion;
	UInt32 runtimeVersion;
	UInt32 editorVersion;
	UInt32 isEditor;
	bool (*RegisterCommand)(CommandInfo* info);
	void (*SetOpcodeBase)(UInt32 opcode);
	void* (*QueryInterface)(UInt32 id);
	PluginHandle (*GetPluginHandle)(void);
	// further members (typed commands, runtime directory, nogore flag, ...) follow in the real header and are not used
};

struct NVSEMessagingInterface
{
	struct Message
	{
		const char* sender;
		UInt32      type;
		UInt32      dataLen;
		void*       data;
	};
	typedef void (*EventCallback)(Message* msg);

	enum
	{
		kVersion = 4
	};

	enum
	{
		kMessage_PostLoad,            // 0  all plugins loaded
		kMessage_ExitGame,
		kMessage_ExitToMainMenu,
		kMessage_LoadGame,
		kMessage_SaveGame,
		kMessage_Precompile,
		kMessage_PreLoadGame,
		kMessage_ExitGame_Console,
		kMessage_PostLoadGame,        // 8
		kMessage_PostPostLoad,        // 9  after every plugin's PostLoad
		kMessage_RuntimeScriptError,
		kMessage_DeleteGame,
		kMessage_RenameGame,
		kMessage_RenameNewGame,
		kMessage_NewGame,
		kMessage_DeleteGameName,
		kMessage_RenameGameName,
		kMessage_RenameNewGameName,
		kMessage_DeferredInit,        // 18 the game's data is loaded, at the main menu
		kMessage_ClearScriptDataCache,
		kMessage_MainGameLoop,
		kMessage_ScriptCompile,
		kMessage_EventListDestroyed,
		kMessage_PostQueryPlugins
	};

	UInt32 version;
	bool (*RegisterListener)(PluginHandle listener, const char* sender, EventCallback handler);
	bool (*Dispatch)(PluginHandle sender, UInt32 messageType, void* data, UInt32 dataLen, const char* receiver);
};

#define MAKE_EXE_VERSION_EX(major, minor, build, sub) ((((major) & 0xFF) << 24) | (((minor) & 0xFF) << 16) | (((build) & 0xFFF) << 4) | ((sub) & 0xF))
#define MAKE_EXE_VERSION(major, minor, build)         MAKE_EXE_VERSION_EX(major, minor, build, 0)
#define GET_EXE_VERSION_MAJOR(a) (((a) & 0xFF000000) >> 24)
#define GET_EXE_VERSION_MINOR(a) (((a) & 0x00FF0000) >> 16)
#define GET_EXE_VERSION_BUILD(a) (((a) & 0x0000FFF0) >> 4)
