using System;
using XRL.World;

namespace XRL.World.Parts
{
    /// <summary>
    /// Sample part in the Copilot workspace — references resolve from your Qud install.
    /// Replace or add files under src/ for your mod.
    /// </summary>
    [Serializable]
    public class QudLabWorkspaceSamplePart : IPart
    {
        public override bool WantEvent(int ID, int cascade)
        {
            return base.WantEvent(ID, cascade);
        }
    }
}
