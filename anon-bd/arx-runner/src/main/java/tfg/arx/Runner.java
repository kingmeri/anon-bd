package tfg.arx;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.deidentifier.arx.ARXAnonymizer;
import org.deidentifier.arx.ARXConfiguration;
import org.deidentifier.arx.ARXResult;
import org.deidentifier.arx.AttributeType;
import org.deidentifier.arx.AttributeType.Hierarchy;
import org.deidentifier.arx.Data;
import org.deidentifier.arx.DataDefinition;
import org.deidentifier.arx.DataHandle;
import org.deidentifier.arx.DataType;

import org.deidentifier.arx.criteria.KAnonymity;
import org.deidentifier.arx.criteria.DistinctLDiversity;
import org.deidentifier.arx.criteria.EntropyLDiversity;
import org.deidentifier.arx.criteria.EqualDistanceTCloseness;
import org.deidentifier.arx.criteria.HierarchicalDistanceTCloseness;
import org.deidentifier.arx.criteria.PrivacyCriterion;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.HashMap;
import java.util.Map;

public class Runner {

    // Cache para guardar las jerarquías reales (AttributeType.Hierarchy)
    private static final Map<String, Hierarchy> HIER_BY_ATTR = new HashMap<>();

    // ---------- utils ----------

    private static boolean isQI(String role) {
        if (role == null) return false;
        String r = role.toLowerCase();
        return r.equals("qi") ||
               r.equals("quasi-identifying") ||
               r.equals("quasi_identifying") ||
               r.equals("quasi-identifying attribute");
    }

    private static AttributeType roleToType(String role) {
        if (role == null) return AttributeType.INSENSITIVE_ATTRIBUTE;
        switch (role.toLowerCase()) {
            case "qi":
            case "quasi-identifying":
            case "quasi_identifying":
            case "quasi-identifying attribute":
                return AttributeType.QUASI_IDENTIFYING_ATTRIBUTE;
            case "sensitive":
            case "sensitive_attribute":
                return AttributeType.SENSITIVE_ATTRIBUTE;
            case "identifying":
            case "identifying_attribute":
                return AttributeType.IDENTIFYING_ATTRIBUTE;
            default:
                return AttributeType.INSENSITIVE_ATTRIBUTE;
        }
    }

    private static DataType<?> dataTypeOf(String dt) {
        if (dt == null) return DataType.STRING;
        switch (dt.toLowerCase()) {
            case "integer":
            case "int":     return DataType.INTEGER;
            case "decimal":
            case "double":
            case "float":   return DataType.DECIMAL;
            case "date":    return DataType.DATE;
            default:        return DataType.STRING;
        }
    }

    private static List<String[]> readCsv(File f, char sep) throws IOException {
        List<String[]> out = new ArrayList<>();
        try (var br = Files.newBufferedReader(f.toPath(), StandardCharsets.UTF_8)) {
            String line;
            while ((line = br.readLine()) != null) {
                out.add(parseCsvLine(line, sep));
            }
        }
        return out;
    }

    private static String[] parseCsvLine(String line, char sep) {
        List<String> cols = new ArrayList<>();
        StringBuilder sb = new StringBuilder();
        boolean inQuotes = false;

        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                // Manejo de comillas dobles escapadas ("")
                if (inQuotes && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    sb.append('"');
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (c == sep && !inQuotes) {
                cols.add(sb.toString());
                sb.setLength(0);
            } else {
                sb.append(c);
            }
        }
        cols.add(sb.toString());
        return cols.toArray(new String[0]);
    }


    private static JsonNode must(JsonNode n, String k) {
        if (n == null || !n.has(k) || n.get(k).isNull()) {
            throw new IllegalArgumentException("Falta clave obligatoria en manifest: " + k);
        }
        return n.get(k);
    }

    // Forzar int (evita error de conversión implícita double→int)
    private static int getIntRounded(JsonNode obj, String key) {
        JsonNode node = must(obj, key);
        if (node.isInt() || node.isLong()) return node.asInt();
        return (int) Math.round(node.asDouble());
    }

    // Soporte para RecursiveCLDiversity según versión (si lo usas)
    private static PrivacyCriterion buildRecursiveCL(String col, int l, double c) {
        try {
            Class<?> clazz = Class.forName("org.deidentifier.arx.criteria.RecursiveCLDiversity");
            try {
                var ctor3 = clazz.getConstructor(String.class, int.class, double.class);
                return (PrivacyCriterion) ctor3.newInstance(col, l, c);
            } catch (NoSuchMethodException ignore) {
                var ctor2 = clazz.getConstructor(String.class, int.class);
                return (PrivacyCriterion) ctor2.newInstance(col, l);
            }
        } catch (Exception e) {
            throw new RuntimeException("No se pudo instanciar RecursiveCLDiversity: " + e.getMessage(), e);
        }
    }

    // ---------- main ----------

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Uso: java -jar arx-runner.jar manifest.json");
            System.exit(2);
        }

        ObjectMapper om = new ObjectMapper();
        JsonNode m = om.readTree(new File(args[0]));

        JsonNode in  = must(m, "input");
        JsonNode out = must(m, "output");

        String inputPath  = must(in, "path").asText();
        char   separator  = in.has("separator") ? in.get("separator").asText(",").charAt(0) : ',';
        char   hSep       = m.has("hierarchy_separator") ? m.get("hierarchy_separator").asText(",").charAt(0) : separator;

        String outputPath = must(out, "path").asText();
        boolean overwrite = !out.has("overwrite") || out.get("overwrite").asBoolean(true);

        File inFile = new File(inputPath);
        if (!inFile.exists()) throw new IllegalArgumentException("Input no existe: " + inputPath);
        if (!overwrite && new File(outputPath).exists()) {
            throw new IllegalArgumentException("Output ya existe y overwrite=false: " + outputPath);
        }

        // Cargar CSV de datos
        Data data = Data.create(inFile, StandardCharsets.UTF_8, separator);
        DataDefinition def = data.getDefinition();

        // Definición de atributos
        JsonNode attrs = must(m, "attributes");
        if (!attrs.isArray()) throw new IllegalArgumentException("'attributes' debe ser array");

        for (JsonNode a : attrs) {
            String name = must(a, "name").asText();
            String role = a.has("role") ? a.get("role").asText() : "insensitive";
            def.setAttributeType(name, roleToType(role));
            if (a.has("data_type")) {
                def.setDataType(name, dataTypeOf(a.get("data_type").asText()));
            }
        }

        // Jerarquías: crear Hierarchy y guardarlo en cache
        for (JsonNode a : attrs) {
            String name = must(a, "name").asText();
            String role = a.has("role") ? a.get("role").asText() : "insensitive";
            if (isQI(role)) {
                if (!a.has("hierarchy"))
                    throw new IllegalArgumentException("QI sin 'hierarchy': " + name);

                String hpath = a.get("hierarchy").asText();
                File hf = new File(hpath);
                if (!hf.exists())
                    throw new IllegalArgumentException("No existe jerarquía para " + name + ": " + hpath);

                List<String[]> hRows = readCsv(hf, hSep);
                Hierarchy h = Hierarchy.create(hRows);
                def.setHierarchy(name, h);
                HIER_BY_ATTR.put(name, h); // cachea el Hierarchy real
            }
        }

        // Privacidad
        JsonNode privacy = must(m, "privacy");
        int k = must(privacy, "k").asInt();
        double suppression = privacy.has("suppression_limit") ? privacy.get("suppression_limit").asDouble(0.0) : 0.0;

        ARXConfiguration config = ARXConfiguration.create();
        config.addPrivacyModel(new KAnonymity(k));
        config.setSuppressionLimit(suppression);

        // l-diversity
        if (privacy.has("l_diversity") && privacy.get("l_diversity").isArray()) {
            for (JsonNode ld : privacy.get("l_diversity")) {
                String col = must(ld, "column").asText();
                int l = must(ld, "l").asInt();
                String type = ld.has("type") ? ld.get("type").asText("distinct").toLowerCase() : "distinct";
                switch (type) {
                    case "distinct":
                        config.addPrivacyModel(new DistinctLDiversity(col, l));
                        break;
                    case "entropy":
                        config.addPrivacyModel(new EntropyLDiversity(col, l));
                        break;
                    case "recursive":
                    case "recursivec": {
                        double c = ld.has("c") ? ld.get("c").asDouble(0.5) : 0.5;
                        config.addPrivacyModel(buildRecursiveCL(col, l, c));
                        break;
                    }
                    default:
                        throw new IllegalArgumentException("Tipo l-diversity no reconocido: " + type);
                }
            }
        }

        // t-closeness (ARX 3.9.2 usa int)
        if (privacy.has("t_closeness") && privacy.get("t_closeness").isArray()) {
            for (JsonNode tc : privacy.get("t_closeness")) {
                final String col  = must(tc, "column").asText();
                final int    tInt = getIntRounded(tc, "t");

                final String dist = tc.has("distance")
                        ? tc.get("distance").asText("equal").toLowerCase()
                        : "equal";

                switch (dist) {
                    case "equal":
                        config.addPrivacyModel(new EqualDistanceTCloseness(col, tInt));
                        break;

                    case "hierarchical": {
                        // 1) intenta usar el Hierarchy real que ya cargamos
                        Hierarchy hh = HIER_BY_ATTR.get(col);

                        // 2) si no está, convierte desde el String[][]
                        if (hh == null) {
                            String[][] mat = def.getHierarchy(col); // en tu ARX devuelve String[][]
                            if (mat != null) {
                                hh = Hierarchy.create(mat); // convertir a AttributeType.Hierarchy
                            }
                        }

                        if (hh == null) {
                            throw new IllegalArgumentException(
                                "t-closeness 'hierarchical' requiere jerarquía en columna: " + col
                            );
                        }

                        config.addPrivacyModel(new HierarchicalDistanceTCloseness(col, tInt, hh));
                        break;
                    }

                    default:
                        throw new IllegalArgumentException("Distancia t-closeness no reconocida: " + dist);
                }
            }
        }

        // Anonimizar
        ARXAnonymizer anonymizer = new ARXAnonymizer();
        ARXResult result = anonymizer.anonymize(data, config);

        DataHandle handle = result.getOutput();
        if (handle == null) {
            throw new IllegalStateException("ARX no generó salida (constraints imposibles o sin solución).");
        }

        // Guardar
        File outFile = new File(outputPath);
        File parent = outFile.getParentFile();
        if (parent != null) parent.mkdirs();
        handle.save(outFile, separator);

        System.out.println("OK: anonimizado → " + outFile.getAbsolutePath());
    }
}
