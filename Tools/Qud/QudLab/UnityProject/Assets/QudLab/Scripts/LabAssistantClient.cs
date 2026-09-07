using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace QudLab.Unity
{
    /// <summary>
    /// Thin HTTP client for the localhost mod-assistant (Phase 3).
    /// Roslyn stays in .NET CLI/serve — Unity only consumes JSON.
    /// </summary>
    public sealed class LabAssistantClient
    {
        public string BaseUrl { get; set; } = "http://127.0.0.1:47821";

        public IEnumerator Get(string path, Action<bool, string> done, int timeoutSeconds = 30)
        {
            using var req = UnityWebRequest.Get(Combine(path));
            req.timeout = timeoutSeconds;
            yield return req.SendWebRequest();
            done(req.result == UnityWebRequest.Result.Success, req.downloadHandler?.text ?? req.error);
        }

        public IEnumerator PostJson(string path, string jsonBody, Action<bool, long, string> done, int timeoutSeconds = 60)
        {
            var body = Encoding.UTF8.GetBytes(string.IsNullOrEmpty(jsonBody) ? "{}" : jsonBody);
            using var req = new UnityWebRequest(Combine(path), "POST");
            req.uploadHandler = new UploadHandlerRaw(body);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            req.timeout = timeoutSeconds;
            yield return req.SendWebRequest();
            done(req.result == UnityWebRequest.Result.Success, req.responseCode, req.downloadHandler?.text ?? req.error);
        }

        string Combine(string path)
        {
            if (string.IsNullOrEmpty(path))
                return BaseUrl.TrimEnd('/');
            if (!path.StartsWith("/"))
                path = "/" + path;
            return BaseUrl.TrimEnd('/') + path;
        }
    }
}
