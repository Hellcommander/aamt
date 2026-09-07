using QudLab.Core.Abstractions;
using QudLab.Core.Binders;
using QudLab.Core.Install;

namespace QudLab.Core;

/// <summary>Composition root for Lab host (Unity or CLI).</summary>
public sealed class LabHost
{
    public OwnershipGate Gate { get; } = new();
    public QudAssemblyBinder Assemblies { get; } = new();
    public QudAssetBinder Assets { get; } = new();
    public InMemoryThreadActionSink ThreadActions { get; } = new();

    public GateResult? LastGate { get; private set; }
    public QudInstallInfo? Install => LastGate?.Install;

    public GateResult Startup(string? overridePath = null)
    {
        var result = Gate.Evaluate(overridePath);
        LastGate = result;
        if (!result.Ok || result.Install is null)
            return result;

        var a = Assemblies.Bind(result.Install);
        if (!a.Ok)
            return a;
        var assets = Assets.Bind(result.Install);
        if (!assets.Ok)
            return assets;

        return GateResult.Success(result.Install,
            $"{result.Message} Assemblies + assets bound. Simulator/assistant stubs ready.");
    }
}
