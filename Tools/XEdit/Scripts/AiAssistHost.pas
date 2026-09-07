{
  AI host for TES5Edit / SF1Edit.
  Reads job.json from ScriptsPath, writes result.json.
  Requires xEdit 4.1.5+ (JsonDataObjects). Starfield ops assume SF1 / -SF1.
}
unit AiAssistHost;

var
  Job: TJsonObject;
  Res: TJsonObject;
  RecArr: TJsonArray;

function FindFile(aName: string): IInterface;
var
  i: integer;
  f: IInterface;
begin
  Result := nil;
  if aName = '' then
    Exit;
  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    if CompareText(GetFileName(f), aName) = 0 then begin
      Result := f;
      Exit;
    end;
  end;
end;

function HexToInt(s: string): Int64;
begin
  Result := 0;
  s := Trim(s);
  if s = '' then Exit;
  if (Length(s) > 2) and (Copy(s, 1, 2) = '0x') then
    Delete(s, 1, 2);
  if (Length(s) > 0) and (s[1] <> '$') then
    s := '$' + s;
  Result := StrToInt64(s);
end;

function FindByEdid(f: IInterface; sig, edid: string): IInterface;
var
  i: integer;
  g: IInterface;
begin
  Result := nil;
  if not Assigned(f) or (edid = '') then Exit;
  if sig <> '' then begin
    g := GroupBySignature(f, sig);
    if Assigned(g) then
      Result := MainRecordByEditorID(g, edid);
    Exit;
  end;
  Result := RecordByEditorID(f, edid);
  if Assigned(Result) then Exit;
  for i := 0 to ElementCount(f) - 1 do begin
    g := ElementByIndex(f, i);
    if Signature(g) = 'TES4' then Continue;
    Result := MainRecordByEditorID(g, edid);
    if Assigned(Result) then Exit;
  end;
end;

function FindRec(f: IInterface): IInterface;
var
  fid: Int64;
begin
  Result := nil;
  if Job.S['formid'] <> '' then begin
    fid := HexToInt(Job.S['formid']);
    Result := RecordByFormID(f, fid, True);
    if Assigned(Result) then Exit;
  end;
  Result := FindByEdid(f, Job.S['signature'], Job.S['edid']);
end;

procedure DumpElem(e: IInterface; obj: TJsonObject; depth, maxDepth: integer);
var
  i, n: integer;
  child: IInterface;
  arr: TJsonArray;
  childObj: TJsonObject;
  linked: IInterface;
begin
  if not Assigned(e) then Exit;
  obj.S['name'] := Name(e);
  obj.S['path'] := Path(e);
  obj.S['value'] := GetEditValue(e);
  linked := LinksTo(e);
  if Assigned(linked) then
    obj.S['linksTo'] := Name(linked);
  if depth >= maxDepth then Exit;
  n := ElementCount(e);
  if n <= 0 then Exit;
  if n > 250 then n := 250;
  arr := obj.A['children'];
  for i := 0 to n - 1 do begin
    child := ElementByIndex(e, i);
    childObj := arr.AddObject;
    DumpElem(child, childObj, depth + 1, maxDepth);
  end;
end;

procedure AddRecSummary(rec: IInterface);
var
  o: TJsonObject;
begin
  if not Assigned(rec) then Exit;
  if not Assigned(RecArr) then
    RecArr := Res.A['records'];
  o := RecArr.AddObject;
  o.S['file'] := GetFileName(GetFile(rec));
  o.S['signature'] := Signature(rec);
  o.S['edid'] := EditorID(rec);
  o.S['formid'] := IntToHex(FormID(rec), 8);
  o.S['name'] := Name(rec);
end;

procedure OpInfo;
var
  i: integer;
  f: IInterface;
  arr: TJsonArray;
  o: TJsonObject;
  j: integer;
begin
  Res.S['game'] := wbAppName;
  Res.S['gameName'] := wbGameName;
  Res.S['master'] := wbGameMasterEsm;
  arr := Res.A['files'];
  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    o := arr.AddObject;
    o.S['name'] := GetFileName(f);
    o.I['loadOrder'] := GetLoadOrder(f);
    o.I['records'] := RecordCount(f);
    o.B['esm'] := GetIsESM(f);
    for j := 0 to MasterCount(f) - 1 do
      o.A['masters'].Add(GetFileName(MasterByIndex(f, j)));
  end;
end;

procedure OpDump;
var
  f, rec: IInterface;
  dump: TJsonObject;
  maxDepth: integer;
begin
  f := FindFile(Job.S['plugin']);
  if not Assigned(f) then begin
    Res.S['error'] := 'plugin not loaded: ' + Job.S['plugin'];
    Res.B['ok'] := False;
    Exit;
  end;
  rec := FindRec(f);
  if not Assigned(rec) then begin
    Res.S['error'] := 'record not found';
    Res.B['ok'] := False;
    Exit;
  end;
  maxDepth := Job.I['maxDepth'];
  if maxDepth <= 0 then maxDepth := 8;
  dump := Res.O['record'];
  dump.S['file'] := GetFileName(GetFile(rec));
  dump.S['signature'] := Signature(rec);
  dump.S['edid'] := EditorID(rec);
  dump.S['formid'] := IntToHex(FormID(rec), 8);
  if Job.S['path'] <> '' then
    dump.S['value'] := GetElementEditValues(rec, Job.S['path'])
  else
    DumpElem(rec, dump, 0, maxDepth);
end;

procedure OpGet;
var
  f, rec: IInterface;
begin
  f := FindFile(Job.S['plugin']);
  rec := FindRec(f);
  if not Assigned(rec) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'record not found';
    Exit;
  end;
  Res.S['value'] := GetElementEditValues(rec, Job.S['path']);
end;

procedure OpSet;
var
  f, rec: IInterface;
begin
  f := FindFile(Job.S['plugin']);
  rec := FindRec(f);
  if not Assigned(rec) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'record not found';
    Exit;
  end;
  if not IsEditable(rec) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'record is not editable (need override in a non-official plugin, or -AllowMasterFilesEdit)';
    Exit;
  end;
  SetElementEditValues(rec, Job.S['path'], Job.S['value']);
  Res.S['value'] := GetElementEditValues(rec, Job.S['path']);
end;

procedure OpRecords;
var
  f, g, rec: IInterface;
  i, n, lim: integer;
  sig, q: string;
begin
  f := FindFile(Job.S['plugin']);
  if not Assigned(f) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'plugin not loaded';
    Exit;
  end;
  sig := Job.S['signature'];
  q := LowerCase(Job.S['query']);
  lim := Job.I['limit'];
  if lim <= 0 then lim := 100;
  n := 0;
  if sig <> '' then begin
    g := GroupBySignature(f, sig);
    if not Assigned(g) then Exit;
    for i := 0 to ElementCount(g) - 1 do begin
      rec := ElementByIndex(g, i);
      if Signature(rec) <> sig then Continue;
      if (q = '') or (Pos(q, LowerCase(EditorID(rec))) > 0) or (Pos(q, LowerCase(Name(rec))) > 0) then begin
        AddRecSummary(rec);
        Inc(n);
        if n >= lim then Exit;
      end;
    end;
  end;
end;

procedure OpCopyOverride;
var
  src, dst, rec, copy: IInterface;
begin
  src := FindFile(Job.S['plugin']);
  dst := FindFile(Job.S['targetPlugin']);
  rec := FindRec(src);
  if not Assigned(rec) or not Assigned(dst) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'source record or target plugin missing';
    Exit;
  end;
  copy := wbCopyElementToFile(rec, dst, False, True);
  AddRecSummary(copy);
end;

procedure OpAddRecord;
var
  f, g, rec: IInterface;
  sig: string;
begin
  f := FindFile(Job.S['plugin']);
  sig := Job.S['signature'];
  if not Assigned(f) or (sig = '') then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'plugin and signature required';
    Exit;
  end;
  g := GroupBySignature(f, sig);
  if not Assigned(g) then
    g := Add(f, sig, True);
  rec := Add(g, sig, True);
  if Job.S['edid'] <> '' then
    SetElementEditValues(rec, 'EDID', Job.S['edid']);
  AddRecSummary(rec);
end;

procedure OpCreatePlugin;
var
  f: IInterface;
  name: string;
begin
  name := Job.S['plugin'];
  if name = '' then name := 'AiNew.esm';
  f := AddNewFileName(name);
  if not Assigned(f) then begin
    Res.B['ok'] := False;
    Res.S['error'] := 'AddNewFileName failed (Starfield prefers .esm; blueprint masters cannot be added)';
    Exit;
  end;
  AddMasterIfMissing(f, wbGameMasterEsm, True);
  Res.S['plugin'] := GetFileName(f);
end;

procedure OpApply;
var
  arr: TJsonArray;
  item: TJsonObject;
  i: integer;
  f, rec: IInterface;
begin
  f := FindFile(Job.S['plugin']);
  arr := Job.A['sets'];
  for i := 0 to arr.Count - 1 do begin
    item := arr.O[i];
    Job.S['edid'] := item.S['edid'];
    Job.S['formid'] := item.S['formid'];
    Job.S['signature'] := item.S['signature'];
    rec := FindRec(f);
    if Assigned(rec) and IsEditable(rec) then
      SetElementEditValues(rec, item.S['path'], item.S['value']);
  end;
end;

function Initialize: integer;
var
  jobFile, outFile, op: string;
  f: IInterface;
begin
  Result := 1;
  jobFile := ScriptsPath + 'job.json';
  outFile := ScriptsPath + 'result.json';
  Res := TJsonObject.Create;
  Res.B['ok'] := True;
  try
    if not FileExists(jobFile) then begin
      Res.B['ok'] := False;
      Res.S['error'] := 'job.json not found: ' + jobFile;
    end else begin
      Job := TJsonObject.Create;
      Job.LoadFromFile(jobFile);
      op := LowerCase(Job.S['op']);
      Res.S['op'] := op;
      if op = 'info' then OpInfo
      else if (op = 'dump') or ((op = 'get') and (Job.S['path'] = '')) then OpDump
      else if op = 'get' then OpGet
      else if op = 'set' then OpSet
      else if (op = 'records') or (op = 'search') then OpRecords
      else if (op = 'copy-override') or (op = 'copyoverride') then OpCopyOverride
      else if (op = 'add-record') or (op = 'addrecord') then OpAddRecord
      else if (op = 'create-plugin') or (op = 'createplugin') then OpCreatePlugin
      else if op = 'apply' then OpApply
      else if op = 'check' then begin
        f := FindFile(Job.S['plugin']);
        Res.S['check'] := Check(FindRec(f));
      end
      else
        OpInfo;
    end;
  except
    on E: Exception do begin
      Res.B['ok'] := False;
      Res.S['error'] := E.Message;
    end;
  end;
  Res.SaveToFile(outFile, False);
  if Assigned(Job) then Job.Free;
  Res.Free;
end;

end.
