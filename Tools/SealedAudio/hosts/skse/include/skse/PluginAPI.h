#pragma once

#include "Types.h"

#include <cstddef>

typedef UInt32 PluginHandle;

struct PluginInfo
{
	enum
	{
		kInfoVersion = 1
	};

	UInt32 infoVersion;
	const char* name;
	UInt32 version;
};

enum
{
	kPluginHandle_Invalid = 0xFFFFFFFF
};

enum
{
	kInterface_Invalid = 0,
	kInterface_Scaleform,
	kInterface_Papyrus,
	kInterface_Serialization,
	kInterface_Task,
	kInterface_Messaging,
	kInterface_Object,
	kInterface_Trampoline,
	kInterface_Max,
	kInterface_VR = 0x10,
};

struct SKSEInterface
{
	UInt32 skseVersion;
	UInt32 runtimeVersion;
	UInt32 editorVersion;
	UInt32 isEditor;
	void* (*QueryInterface)(UInt32 id);
	PluginHandle (*GetPluginHandle)(void);
	UInt32 (*GetReleaseIndex)(void);
	const PluginInfo* (*GetPluginInfo)(const char* name);
};

struct SKSEMessagingInterface
{
	struct Message
	{
		const char* sender;
		UInt32 type;
		UInt32 dataLen;
		void* data;
	};

	typedef void (*EventCallback)(Message* msg);

	enum
	{
		kInterfaceVersion = 2
	};

	enum
	{
		kMessage_PostLoad = 0,
		kMessage_PostPostLoad,
		kMessage_PreLoadGame,
		kMessage_PostLoadGame,
		kMessage_SaveGame,
		kMessage_DeleteGame,
		kMessage_InputLoaded,
		kMessage_NewGame,
		kMessage_DataLoaded
	};

	UInt32 interfaceVersion;
	bool (*RegisterListener)(PluginHandle listener, const char* sender, EventCallback handler);
	bool (*Dispatch)(PluginHandle sender, UInt32 messageType, void* data, UInt32 dataLen, const char* receiver);
};

struct SKSETrampolineInterface
{
	enum
	{
		kInterfaceVersion = 1
	};

	UInt32 interfaceVersion;
	void* (*AllocateFromBranchPool)(PluginHandle plugin, size_t size);
	void* (*AllocateFromLocalPool)(PluginHandle plugin, size_t size);
};

class TaskDelegate
{
public:
	virtual void Run() = 0;
	virtual void Dispose() = 0;
};

struct SKSETaskInterface
{
	enum
	{
		kInterfaceVersion = 2
	};

	UInt32 interfaceVersion;
	void (*AddTask)(TaskDelegate* task);
	void (*AddUITask)(void* task);
};

struct SKSEVRInterface
{
	enum
	{
		kInterfaceVersion = 1
	};

	UInt32 interfaceVersion;
	UInt32 openvrSourceVersion;
	UInt32 openvrTargetVersion;

	typedef void (*ControllerStateCallback)(UInt32 device, void* state, UInt32 stateSize, bool& allow);
	typedef bool (*WaitGetPosesCallback)(void* renderPoses, UInt32 renderCount, void* gamePoses, UInt32 gameCount);

	bool (*IsActionsEnabled)();
	void (*RegisterForControllerState)(PluginHandle plugin, SInt32 sortOrder, ControllerStateCallback callback);
	void (*RegisterForPoses)(PluginHandle plugin, SInt32 sortOrder, WaitGetPosesCallback callback);
};

struct SKSEPluginVersionData
{
	enum
	{
		kVersion = 1,
	};

	enum
	{
		kVersionIndependent_AddressLibraryPostAE = 1 << 0,
		kVersionIndependent_Signatures = 1 << 1,
		kVersionIndependent_StructsPost629 = 1 << 2,
	};

	enum
	{
		kVersionIndependentEx_NoStructUse = 1 << 0,
		kVersionIndependentEx_AddressLibraryV5 = 1 << 1,
	};

	UInt32 dataVersion;
	UInt32 pluginVersion;
	char name[256];
	char author[256];
	char supportEmail[252];
	UInt32 versionIndependenceEx;
	UInt32 versionIndependence;
	UInt32 compatibleVersions[16];
	UInt32 seVersionRequired;
};
