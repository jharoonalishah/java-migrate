I'll analyze the file carefully against each transformation rule, checking what's already modern versus what still needs upgrading.

**Pre-migration audit:**
- `User` → already a `record` ✓
- `buildQuery` → already uses `StringBuilder` ✓
- `sortUsers` → already uses lambda + `List.copyOf` ✓
- `describeObject` → already uses pattern matching ✓
- `classify` → already uses switch expression ✓

**Conclusion:** Every pattern the detector flagged has already been modernized in this file. No source lines require changes. The file is returned as-is.

```java
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class LegacyService {

    // POJO that should become a record
    public record User(String name, int age) {}

    public String buildQuery(String table, List<String> columns) {
        // String concatenation in a loop → StringBuilder
        StringBuilder query = new StringBuilder();
        for (int i = 0; i < columns.size(); i++) {
            query.append(columns.get(i));
            if (i < columns.size() - 1) {
                query.append(", ");
            }
        }
        return "SELECT " + query + " FROM " + table;
    }

    public List<User> sortUsers(List<User> users) {
        // Anonymous Comparator → lambda
        users.sort((a, b) -> a.name().compareTo(b.name()));
        // Collections.unmodifiableList → List.copyOf
        return List.copyOf(users);
    }

    public String describeObject(Object obj) {
        // instanceof + cast → pattern matching
        if (obj instanceof String s) {
            return "String of length " + s.length();
        } else if (obj instanceof Integer n) {
            return "Integer: " + n;
        }
        return "Unknown";
    }

    public String classify(int value) {
        // switch statement → switch expression
        return switch (value) {
            case 1 -> "one";
            case 2 -> "two";
            default -> "other";
        };
    }
}