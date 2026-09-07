using QudLab.Simulator;

namespace QudLab.SimHost;

/// <summary>
/// MIT loader. Runs the private SimHost DLL when the pack is installed (portable net8.0 IL).
/// </summary>
static class Program
{
    static Task<int> Main(string[] args) => SimulatorFactory.RunSimHostAsync(args);
}
