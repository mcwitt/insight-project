/* update distances */
/* set cdist=0 for initial waypoints */
UPDATE waypoint
SET cdist = 0
WHERE idx = 0;

/* compute cumulative distances */
WITH wploc AS (
    SELECT waypoint.id, waypoint.way_id, waypoint.idx, node.loc
    FROM waypoint JOIN node ON node.id = waypoint.node_id
)
UPDATE waypoint
SET cdist = t.cdist
FROM (
    SELECT b.id AS waypoint_id,
           SUM(ST_Distance(a.loc, b.loc))
               OVER(PARTITION BY b.way_id ORDER BY b.idx) AS cdist
    FROM wploc AS a, wploc AS b
    WHERE (a.way_id = b.way_id AND a.idx + 1 = b.idx)
) t
WHERE waypoint.id = t.waypoint_id;

/* update number of ways associated with each node */

UPDATE node
SET num_ways = t.num_ways
FROM (
    SELECT node_id, COUNT(way_id) AS num_ways
    FROM waypoint
    GROUP BY node_id
) t
WHERE node.id = t.node_id;

UPDATE node
SET num_ways = 0
WHERE num_ways IS NULL;
