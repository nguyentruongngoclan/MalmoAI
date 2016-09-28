package net.minecraftforge.common.property;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import net.minecraft.block.Block;
import net.minecraft.block.properties.IProperty;
import net.minecraft.block.state.BlockState;
import net.minecraft.block.state.BlockState.StateImplementation;
import net.minecraft.block.state.IBlockState;

import com.google.common.base.Optional;
import com.google.common.base.Predicates;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableTable;
import com.google.common.collect.Iterables;

import net.minecraft.block.state.BlockState.StateImplementation;
public class ExtendedBlockState extends BlockState
{
    private final ImmutableSet<IUnlistedProperty<?>> unlistedProperties;

    public ExtendedBlockState(Block blockIn, IProperty[] properties, IUnlistedProperty<?>[] unlistedProperties)
    {
        super(blockIn, properties, buildUnlistedMap(unlistedProperties));
        ImmutableSet.Builder<IUnlistedProperty<?>> builder = ImmutableSet.<IUnlistedProperty<?>>builder();
        for(IUnlistedProperty<?> property : unlistedProperties)
        {
            builder.add(property);
        }
        this.unlistedProperties = builder.build();
    }

    private static ImmutableMap<IUnlistedProperty<?>, Optional<?>> buildUnlistedMap(IUnlistedProperty<?>[] unlistedProperties)
    {
        ImmutableMap.Builder<IUnlistedProperty<?>, Optional<?>> builder = ImmutableMap.<IUnlistedProperty<?>, Optional<?>>builder();
        for(IUnlistedProperty<?> p : unlistedProperties)
        {
            builder.put(p, Optional.absent());
        }
        return builder.build();
    }

    @Override
    protected StateImplementation createState(Block block, ImmutableMap properties, ImmutableMap unlistedProperties)
    {
        if (unlistedProperties == null || unlistedProperties.isEmpty()) return super.createState(block, properties, unlistedProperties);
        return new ExtendedStateImplementation(block, properties, unlistedProperties, null);
    }

    protected static class ExtendedStateImplementation extends StateImplementation implements IExtendedBlockState
    {
        private final ImmutableMap<IUnlistedProperty<?>, Optional<?>> unlistedProperties;
        private Map<Map<IProperty, Comparable>, IBlockState> normalMap;

        protected ExtendedStateImplementation(Block block, ImmutableMap properties, ImmutableMap<IUnlistedProperty<?>, Optional<?>> unlistedProperties, ImmutableTable<IProperty, Comparable, IBlockState> table)
        {
            super(block, properties);
            this.unlistedProperties = unlistedProperties;
            this.propertyValueTable = table;
        }

        /**
         * Get a version of this BlockState with the given Property now set to the given value
         */
        @Override
        public IBlockState withProperty(IProperty property, Comparable value)
        {
            if (!this.getProperties().containsKey(property))
            {
                throw new IllegalArgumentException("Cannot set property " + property + " as it does not exist in " + getBlock().getBlockState());
            }
            else if (!property.getAllowedValues().contains(value))
            {
                throw new IllegalArgumentException("Cannot set property " + property + " to " + value + " on block " + Block.blockRegistry.getNameForObject(getBlock()) + ", it is not an allowed value");
            }
            else
            {
                if(this.getProperties().get(property) == value)
                {
                    return this;
                }
                Map<IProperty, Comparable> map = new HashMap<IProperty, Comparable>(getProperties());
                map.put(property, value);
                if(Iterables.all(unlistedProperties.values(), Predicates.<Optional<?>>equalTo(Optional.absent())))
                { // no dynamic properties present, looking up in the normal table
                    return (IExtendedBlockState) normalMap.get(map);
                }
                ImmutableTable<IProperty, Comparable, IBlockState> table = propertyValueTable;
                table = ((StateImplementation)table.get(property, value)).getPropertyValueTable();
                return new ExtendedStateImplementation(getBlock(), ImmutableMap.copyOf(map), unlistedProperties, table).setMap(this.normalMap);
            }
        }

        public <V> IExtendedBlockState withProperty(IUnlistedProperty<V> property, V value)
        {
            if(!this.unlistedProperties.containsKey(property))
            {
                throw new IllegalArgumentException("Cannot set unlisted property " + property + " as it does not exist in " + getBlock().getBlockState());
            }
            if(!property.isValid(value))
            {
                throw new IllegalArgumentException("Cannot set unlisted property " + property + " to " + value + " on block " + Block.blockRegistry.getNameForObject(getBlock()) + ", it is not an allowed value");
            }
            Map<IUnlistedProperty<?>, Optional<?>> newMap = new HashMap<IUnlistedProperty<?>, Optional<?>>(unlistedProperties);
            newMap.put(property, Optional.fromNullable(value));
            if(Iterables.all(newMap.values(), Predicates.<Optional<?>>equalTo(Optional.absent())))
            { // no dynamic properties, lookup normal state
                return (IExtendedBlockState) normalMap.get(getProperties());
            }
            return new ExtendedStateImplementation(getBlock(), getProperties(), ImmutableMap.copyOf(newMap), propertyValueTable).setMap(this.normalMap);
        }

        public Collection<IUnlistedProperty<?>> getUnlistedNames()
        {
            return Collections.unmodifiableCollection(unlistedProperties.keySet());
        }

        public <V>V getValue(IUnlistedProperty<V> property)
        {
            if(!this.unlistedProperties.containsKey(property))
            {
                throw new IllegalArgumentException("Cannot get unlisted property " + property + " as it does not exist in " + getBlock().getBlockState());
            }
            return property.getType().cast(this.unlistedProperties.get(property).orNull());
        }

        public ImmutableMap<IUnlistedProperty<?>, Optional<?>> getUnlistedProperties()
        {
            return unlistedProperties;
        }

        @Override
        public void buildPropertyValueTable(Map map)
        {
            this.normalMap = map;
            super.buildPropertyValueTable(map);
        }
        
        private ExtendedStateImplementation setMap(Map<Map<IProperty, Comparable>, IBlockState> map)
        {
            this.normalMap = map;
            return this;
        }
        
        public IBlockState getClean()
        {
            return this.normalMap.get(getProperties());
        }
    }
}