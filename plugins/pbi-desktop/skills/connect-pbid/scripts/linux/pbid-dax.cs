// Run one DAX (or DMV) query against Power BI Desktop's local Analysis Services instance and
// write the result as JSON. Built and run by pbid-dax.sh inside Desktop's Wine prefix.
// Usage: pbid-dax.exe <port> <query file> <output file>
using System;
using System.Data;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;

static class PbidDax
{
    const string Bin = @"C:\Program Files\Microsoft Power BI Desktop\bin";

    static string Quote(string s)
    {
        var b = new StringBuilder("\"");
        foreach (char c in s)
        {
            if (c == '"' || c == '\\') b.Append('\\').Append(c);
            else if (c == '\n') b.Append("\\n");
            else if (c == '\r') b.Append("\\r");
            else if (c == '\t') b.Append("\\t");
            else if (c < ' ') b.Append("\\u").Append(((int)c).ToString("x4"));
            else b.Append(c);
        }
        return b.Append('"').ToString();
    }

    static string Value(object v)
    {
        if (v == null || v is DBNull) return "null";
        if (v is bool) return (bool)v ? "true" : "false";
        if (v is DateTime) return Quote(((DateTime)v).ToString("s", CultureInfo.InvariantCulture));
        if (v is double || v is float)
        {
            double d = Convert.ToDouble(v);
            return double.IsNaN(d) || double.IsInfinity(d) ? "null" : d.ToString("R", CultureInfo.InvariantCulture);
        }
        if (v is decimal || v is long || v is int || v is short || v is byte)
            return Convert.ToString(v, CultureInfo.InvariantCulture);
        return Quote(Convert.ToString(v, CultureInfo.InvariantCulture));
    }

    static int Main(string[] args)
    {
        var json = new StringBuilder();
        int code = 0;
        try
        {
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                string candidate = Path.Combine(Bin, new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
            };
            // Desktop's own ADOMD client, loaded by reflection so nothing is needed at compile time.
            Assembly adomd = Assembly.LoadFrom(Path.Combine(Bin, "Microsoft.PowerBI.AdomdClient.dll"));
            Type type = adomd.GetType("Microsoft.AnalysisServices.AdomdClient.AdomdConnection", true);
            string query = File.ReadAllText(args[1], Encoding.UTF8);
            using (var conn = (IDbConnection)Activator.CreateInstance(type, "Data Source=localhost:" + args[0] + ";Connect Timeout=15;"))
            {
                conn.Open();
                using (IDbCommand cmd = conn.CreateCommand())
                {
                    cmd.CommandText = query;
                    cmd.CommandTimeout = 120;
                    using (IDataReader reader = cmd.ExecuteReader())
                    {
                        json.Append("{\"columns\":[");
                        for (int i = 0; i < reader.FieldCount; i++)
                            json.Append(i > 0 ? "," : "").Append(Quote(reader.GetName(i)));
                        json.Append("],\"rows\":[");
                        int rows = 0;
                        while (reader.Read())
                        {
                            json.Append(rows++ > 0 ? ",\n[" : "\n[");
                            for (int i = 0; i < reader.FieldCount; i++)
                                json.Append(i > 0 ? "," : "").Append(Value(reader.GetValue(i)));
                            json.Append("]");
                        }
                        json.Append("\n],\"rowCount\":").Append(rows).Append("}");
                    }
                }
            }
        }
        catch (Exception e)
        {
            Exception inner = e is TargetInvocationException && e.InnerException != null ? e.InnerException : e;
            json.Length = 0;
            json.Append("{\"error\":").Append(Quote(inner.GetType().Name + ": " + inner.Message)).Append("}");
            code = 1;
        }
        File.WriteAllText(args[2], json.ToString() + "\n", new UTF8Encoding(false));
        return code;
    }
}
